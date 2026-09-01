"""Orchestration for the three stateless local-demo endpoints.

Each function here does exactly one unit of protected work and returns
its result -- no database, no queue, no polling. The protected modules
themselves (`FasterWhisperTranscriber`, `PyAvAudioInspector`,
`draft_report`, `run_visual_audit`, `suggested_amount_cents`,
`convert_usd_cents`, `ReportLabPdfRenderer`) are called exactly as the
durable workflow used to call them; only the surrounding persistence and
retry machinery is gone. See `docs/architecture/ai.md` and
`docs/adr/000X-local-demo-downgrade.md` for the full rationale.
"""

from __future__ import annotations

import asyncio
import logging

from jobact.contexts.reports.domain.pricing import (
    suggested_amount_cents,
)
from jobact.contracts.errors.v1.envelope import ApiError
from jobact.contracts.http.v1.demo import (
    AnalyzeContextRequest,
    AnalyzeResponse,
    CheckPdfContextRequest,
    MaterialDto,
    TranscribeResponse,
)
from jobact.shared.application.ai_connectors import NoAiConnectorConfigured
from jobact.shared.application.fx import convert_usd_cents, provided_price_usd
from jobact.shared.application.ports import AiConnector
from jobact.shared.infrastructure.config import Settings, get_settings
from jobact.shared.infrastructure.llm.connectors import build_ai_connector
from jobact.shared.infrastructure.pdf.reportlab_renderer import ReportLabPdfRenderer
from jobact.shared.infrastructure.stt.faster_whisper import FasterWhisperTranscriber
from jobact.shared.infrastructure.stt.pyav_inspector import PyAvAudioInspector
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    MAX_AUDIO_BYTES,
    MAX_TRANSCRIPT_CHARS,
    MIN_TRANSCRIPT_CHARS,
    AudioInvalidError,
    AudioTooLongError,
    TranscriptionUnavailableError,
)
from jobact.workflows.report_fulfillment.agent import (
    ReportAnalysisContext,
    draft_report,
)
from jobact.workflows.report_fulfillment.failures import (
    classify_analysis_failures,
)
from jobact.workflows.visual_audit.agent import run_visual_audit

logger = logging.getLogger(__name__)

_MAX_PHOTO_PAIRS = 6
_AUDIO_CONTENT_TYPES = {"audio/webm", "audio/mp4"}

# Same mapping the durable workflow used: the interface locale decides the
# language every AI-generated, human-readable field is written in.
_RESPONSE_LANGUAGE_BY_LOCALE = {"en-US": "English", "ru-RU": "Russian"}

# Module-level singletons: both are stateless, and the Whisper model is
# expensive to load, so it is loaded once per process, exactly as the old
# stt worker loaded it once per process.
_TRANSCRIBER = FasterWhisperTranscriber()
_AUDIO_INSPECTOR = PyAvAudioInspector()
_PDF_RENDERER = ReportLabPdfRenderer()


def get_ai_connector() -> AiConnector:
    """FastAPI dependency: the single Qwen connector, or a 503 if
    `DASHSCOPE_API_KEY` is not set.
    """
    try:
        return build_ai_connector(get_settings())
    except NoAiConnectorConfigured as exc:
        raise ApiError(
            status=503,
            type="ai-not-configured",
            title="Service Unavailable",
            detail=str(exc),
        ) from exc


async def transcribe(data: bytes, content_type: str) -> TranscribeResponse:
    """Run the protected STT pipeline on one recording: validate ->
    inspect -> transcribe -> validate the transcript. Raises `ApiError`
    for every rejection, using the same failure vocabulary
    (`failures.py`) the durable workflow used.
    """
    if content_type not in _AUDIO_CONTENT_TYPES:
        raise ApiError(
            status=422,
            type="audio-invalid",
            title="Unprocessable Entity",
            detail="The recording is not valid WebM/Opus or MP4/AAC audio.",
        )
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise ApiError(
            status=413,
            type="audio-too-large",
            title="Payload Too Large",
            detail="The recording exceeds the 25 MiB limit.",
        )

    try:
        inspection = await _AUDIO_INSPECTOR.inspect(data, content_type)
    except AudioTooLongError as exc:
        raise ApiError(
            status=422,
            type="audio-too-long",
            title="Unprocessable Entity",
            detail="The recording exceeds the 10 minute limit.",
        ) from exc
    except AudioInvalidError as exc:
        raise ApiError(
            status=422,
            type="audio-invalid",
            title="Unprocessable Entity",
            detail="The recording is not valid WebM/Opus or MP4/AAC audio.",
        ) from exc

    try:
        transcription = await _TRANSCRIBER.transcribe(data, content_type)
    except TranscriptionUnavailableError as exc:
        raise ApiError(
            status=503,
            type="transcription-unavailable",
            title="Service Unavailable",
            detail="Transcription is temporarily unavailable. Please try again.",
        ) from exc

    transcript = transcription.text.strip()
    if not transcript or len(transcript) < MIN_TRANSCRIPT_CHARS or len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise ApiError(
            status=422,
            type="transcription-empty",
            title="Unprocessable Entity",
            detail="No speech could be transcribed from the recording.",
        )

    logger.info(
        "demo_transcription_succeeded transcript_chars=%s language=%s "
        "duration_seconds=%.1f",
        len(transcript),
        transcription.language,
        inspection.duration_seconds,
    )
    return TranscribeResponse(
        transcript=transcript,
        detected_language=transcription.language,
        duration_seconds=inspection.duration_seconds,
    )


async def analyze(
    *,
    context: AnalyzeContextRequest,
    image_pairs: list[tuple[bytes, str, bytes, str]],
    connector: AiConnector,
    settings: Settings,
) -> AnalyzeResponse:
    """Run the protected two-call AI analysis: draft the report, then
    visually audit it against the before/after photos. Both calls must
    succeed -- the same all-or-nothing rule the durable workflow used --
    or the whole analysis is reported as failed.
    """
    if not image_pairs:
        raise ApiError(
            status=409,
            type="evidence-incomplete",
            title="Conflict",
            detail="At least one before/after photo pair is required.",
        )
    image_pairs = image_pairs[:_MAX_PHOTO_PAIRS]

    response_language = _RESPONSE_LANGUAGE_BY_LOCALE.get(context.locale, "English")
    analysis_context = ReportAnalysisContext(
        raw_notes=context.raw_notes,
        customer_name=context.customer_name,
        customer_address=context.customer_address,
        customer_service_type=context.customer_service_type,
        gps_lat=context.gps_lat,
        gps_lon=context.gps_lon,
        currency=context.currency,
        response_language=response_language,
    )

    errors: list[Exception] = []
    try:
        drafting_result = await draft_report(connector, analysis_context)
    except Exception as exc:
        errors.append(exc)
        raise _analysis_failure(errors) from exc
    drafted = drafting_result.draft

    base_usd_cents = suggested_amount_cents(drafted.estimated_work_units)
    converted_amount_cents = convert_usd_cents(
        base_usd_cents, context.currency, settings.usd_rub_rate
    )

    try:
        audit_result = await run_visual_audit(
            connector,
            work_description=drafted.work_completed,
            provided_price_usd=provided_price_usd(
                converted_amount_cents, context.currency, settings.usd_rub_rate
            ),
            image_pairs=image_pairs,
            customer_service_type=context.customer_service_type,
            gps_lat=context.gps_lat,
            gps_lon=context.gps_lon,
            response_language=response_language,
        )
    except Exception as exc:
        errors.append(exc)
        raise _analysis_failure(errors) from exc

    logger.info(
        "demo_analysis_succeeded drafting_model=%s audit_model=%s "
        "estimated_work_units=%s photo_pair_count=%s",
        drafting_result.model,
        audit_result.model,
        drafted.estimated_work_units,
        len(image_pairs),
    )
    return AnalyzeResponse(
        work_completed=drafted.work_completed,
        materials=[
            MaterialDto(label=material.label, qty=material.qty)
            for material in drafted.materials
        ],
        estimated_work_units=drafted.estimated_work_units,
        suggested_amount_cents=converted_amount_cents,
        currency=context.currency,
        confidence=drafted.confidence,
        visual_comparison=audit_result.result,
    )


def _analysis_failure(errors: list[Exception]) -> ApiError:
    failure = classify_analysis_failures(errors)
    return ApiError(
        status=failure.http_status,
        type=failure.code.lower().replace("_", "-"),
        title="AI analysis failed",
        detail=failure.message,
    )


async def render_check_pdf(
    context: CheckPdfContextRequest, signature_png: bytes
) -> bytes:
    """Render the signed customer check, exactly as `GeneratePdfActivity`
    rendered it, minus the report/media persistence around the call.
    """
    settings = get_settings()
    amount = (
        f"{context.amount_cents / 100:.2f} {context.currency}"
        if context.amount_cents is not None
        else f"Not specified ({context.currency})"
    )
    pdf_context = {
        "header": "JobAct Service Report",
        "report_number": context.report_number,
        "customer": {
            "name": context.customer_name,
            "address": context.customer_address,
            "phone": context.customer_phone,
            "service_type": context.customer_service_type,
        },
        "timestamp": context.timestamp,
        "gps": {"latitude": context.gps_lat, "longitude": context.gps_lon},
        "work_completed": context.work_completed,
        "materials": [
            {"label": material.label, "qty": material.qty}
            for material in context.materials
        ],
        "amount": amount,
        "signature_png": signature_png,
        "signer_name": context.signer_name,
    }
    try:
        return await asyncio.wait_for(
            _PDF_RENDERER.render(pdf_context),
            timeout=settings.pdf_render_timeout_seconds,
        )
    except TimeoutError as exc:
        raise ApiError(
            status=504,
            type="pdf-render-timeout",
            title="Gateway Timeout",
            detail="Rendering the check timed out. Please try again.",
        ) from exc
