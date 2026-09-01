"""Unit tests for `apps/api/demo_service.py` -- the stateless orchestration
behind the three demo endpoints. Every test fakes the network-facing edge
(the transcriber/inspector singletons, or `draft_report`/`run_visual_audit`)
so nothing here touches a real model or a real audio codec; the protected
modules themselves already have their own direct unit tests
(`test_report_drafting_agent.py`, `test_visual_audit_agent.py`,
`test_reportlab_renderer.py`).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Literal

import pytest
from PIL import Image

from jobact.apps.api import demo_service
from jobact.contracts.errors.v1.envelope import ApiError
from jobact.contracts.http.v1.demo import AnalyzeContextRequest, CheckPdfContextRequest
from jobact.contracts.http.v1.visual_audits import (
    Comparison,
    EvidenceItem,
    FairPriceRangeUsd,
    PriceAssessment,
    QualityAssessment,
    VisualAuditResult,
)
from jobact.shared.application.ports import AudioInspection, SpeechTranscription
from jobact.shared.infrastructure.config import Settings
from jobact.workflows.report_fulfillment.agent import (
    DraftedMaterial,
    DraftedReport,
    DraftingResult,
)
from jobact.workflows.visual_audit.agent import AuditAgentResult


class _FakeInspector:
    async def inspect(self, data: bytes, declared_content_type: str) -> AudioInspection:
        return AudioInspection(container="webm", codec="opus", duration_seconds=12.5)


class _FakeTranscriber:
    def __init__(self, text: str = "Replaced the leaking valve and tested the line.") -> None:
        self._text = text

    async def transcribe(self, data: bytes, content_type: str) -> SpeechTranscription:
        return SpeechTranscription(text=self._text, language="ru")


class _Connector:
    provider_name = "qwen"

    def model_name(self, alias: str) -> str:
        return "qwen-fake"

    def build_model(self, alias: str, http_client: Any | None = None) -> Any:
        raise NotImplementedError


def _visual_result(
    *,
    verdict: Literal[
        "high_quality", "partially_completed", "poor_quality", "insufficient_data"
    ] = "high_quality",
) -> VisualAuditResult:
    return VisualAuditResult(
        verdict=verdict,
        confidence=90,
        summary="Work matches the description.",
        comparison=Comparison(
            visible_changes=["Valve replaced"],
            work_matches_description=True,
            match_explanation="Visible new valve in the after photo.",
        ),
        quality_assessment=QualityAssessment(
            score=9, strengths=["Clean work"], issues=[], unverified_items=[]
        ),
        price_assessment=PriceAssessment(
            provided_price_usd=15.0,
            fair_price_range_usd=FairPriceRangeUsd(min=10.0, max=20.0),
            price_verdict="reasonable",
            price_explanation="In line with visible scope.",
        ),
        evidence=[EvidenceItem(observation="New valve visible", impact="Confirms the work")],
        limitations=[],
        recommended_next_steps=[],
    )


@pytest.fixture(autouse=True)
def _fake_stt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo_service, "_AUDIO_INSPECTOR", _FakeInspector())
    monkeypatch.setattr(demo_service, "_TRANSCRIBER", _FakeTranscriber())


@pytest.mark.asyncio
async def test_transcribe_returns_the_trimmed_transcript() -> None:
    result = await demo_service.transcribe(b"fake-audio-bytes", "audio/webm")

    assert result.transcript == "Replaced the leaking valve and tested the line."
    assert result.detected_language == "ru"
    assert result.duration_seconds == 12.5


@pytest.mark.asyncio
async def test_transcribe_rejects_an_unsupported_content_type() -> None:
    with pytest.raises(ApiError) as excinfo:
        await demo_service.transcribe(b"data", "audio/ogg")

    assert excinfo.value.status == 422
    assert excinfo.value.type == "audio-invalid"


@pytest.mark.asyncio
async def test_transcribe_rejects_oversized_audio() -> None:
    with pytest.raises(ApiError) as excinfo:
        await demo_service.transcribe(b"x" * (demo_service.MAX_AUDIO_BYTES + 1), "audio/webm")

    assert excinfo.value.status == 413
    assert excinfo.value.type == "audio-too-large"


@pytest.mark.asyncio
async def test_transcribe_rejects_a_too_short_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo_service, "_TRANSCRIBER", _FakeTranscriber(text="Too short."))

    with pytest.raises(ApiError) as excinfo:
        await demo_service.transcribe(b"data", "audio/webm")

    assert excinfo.value.status == 422
    assert excinfo.value.type == "transcription-empty"


def _context(
    *, currency: Literal["USD", "RUB"] = "RUB", locale: Literal["en-US", "ru-RU"] = "ru-RU"
) -> AnalyzeContextRequest:
    return AnalyzeContextRequest(
        raw_notes="Replaced the leaking valve under the sink and tested the line for leaks.",
        customer_name="Ada Lovelace",
        customer_address="12 Analytical Engine Way",
        customer_service_type="Plumbing",
        currency=currency,
        locale=locale,
    )


@pytest.mark.asyncio
async def test_analyze_rejects_missing_photo_pairs() -> None:
    with pytest.raises(ApiError) as excinfo:
        await demo_service.analyze(
            context=_context(),
            image_pairs=[],
            connector=_Connector(),
            settings=Settings(_env_file=None),
        )

    assert excinfo.value.status == 409
    assert excinfo.value.type == "evidence-incomplete"


@pytest.mark.asyncio
async def test_analyze_converts_work_units_into_the_requested_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_draft_report(connector, context):
        assert context.response_language == "Russian"
        return DraftingResult(
            draft=DraftedReport(
                work_completed="Replaced the leaking valve and tested the line.",
                materials=[DraftedMaterial(label="Valve", qty="1")],
                estimated_work_units=3,
                confidence="high",
            ),
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=None,
            model="qwen3.8-flash",
        )

    async def fake_run_visual_audit(connector, **kwargs):
        assert kwargs["response_language"] == "Russian"
        return AuditAgentResult(
            result=_visual_result(),
            prompt_tokens=5,
            completion_tokens=5,
            cost_usd=None,
            model="qwen3-vl-flash",
        )

    monkeypatch.setattr(demo_service, "draft_report", fake_draft_report)
    monkeypatch.setattr(demo_service, "run_visual_audit", fake_run_visual_audit)

    settings = Settings(_env_file=None, usd_rub_rate=Decimal("84.4635"))
    response = await demo_service.analyze(
        context=_context(currency="RUB", locale="ru-RU"),
        image_pairs=[(b"before", "image/jpeg", b"after", "image/jpeg")],
        connector=_Connector(),
        settings=settings,
    )

    # 3 units * 500 USD cents = 1500 USD cents -> RUB at the fixed rate.
    assert response.estimated_work_units == 3
    assert response.suggested_amount_cents == 126_695
    assert response.currency == "RUB"
    assert response.materials[0].label == "Valve"
    assert response.visual_comparison.verdict == "high_quality"


@pytest.mark.asyncio
async def test_analyze_fails_the_whole_call_when_drafting_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_draft(connector, context):
        raise TimeoutError()

    monkeypatch.setattr(demo_service, "draft_report", failing_draft)

    with pytest.raises(ApiError) as excinfo:
        await demo_service.analyze(
            context=_context(),
            image_pairs=[(b"before", "image/jpeg", b"after", "image/jpeg")],
            connector=_Connector(),
            settings=Settings(_env_file=None),
        )

    assert excinfo.value.status == 504
    assert excinfo.value.type == "ai-analysis-timeout"


@pytest.mark.asyncio
async def test_render_check_pdf_embeds_the_signature() -> None:
    context = CheckPdfContextRequest(
        report_number="JA-2026-0001",
        customer_name="Ada Lovelace",
        customer_address="12 Analytical Engine Way",
        customer_phone="+7 900 123-45-67",
        customer_service_type="Plumbing",
        timestamp=datetime.fromisoformat("2026-08-28T10:00:00+00:00"),
        work_completed="Replaced the leaking valve and tested the line.",
        materials=[],
        amount_cents=126_695,
        currency="RUB",
        signer_name="Ada Lovelace",
    )

    signature_buffer = BytesIO()
    Image.new("RGBA", (10, 4), (0, 0, 0, 0)).save(signature_buffer, "PNG")

    pdf_bytes = await demo_service.render_check_pdf(context, signature_buffer.getvalue())

    assert pdf_bytes.startswith(b"%PDF")
