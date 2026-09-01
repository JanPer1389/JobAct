"""The three stateless endpoints behind the local demo: transcribe one
recording, run the unified AI analysis on one job, and render one signed
check PDF. No request here reads or writes any server-side state --
every input arrives as multipart bytes and every output is returned
directly, matching the browser-local persistence design (see
`docs/architecture/overview.md`).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel, ValidationError

from jobact.apps.api.demo_service import (
    analyze,
    get_ai_connector,
    render_check_pdf,
    transcribe,
)
from jobact.contracts.errors.v1.envelope import ApiError, ErrorDetail
from jobact.contracts.http.v1.demo import (
    AnalyzeContextRequest,
    AnalyzeResponse,
    CheckPdfContextRequest,
    TranscribeResponse,
)
from jobact.shared.application.ports import AiConnector
from jobact.shared.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


def _parse_json_field[ModelT: BaseModel](raw: str, model: type[ModelT]) -> ModelT:
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise ApiError(
            status=422,
            type="validation-error",
            title="Unprocessable Entity",
            detail="The context field is invalid.",
            errors=[
                ErrorDetail(loc=[str(part) for part in error["loc"]], message=error["msg"])
                for error in exc.errors()
            ],
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ApiError(
            status=422,
            type="validation-error",
            title="Unprocessable Entity",
            detail="The context field is not valid JSON.",
        ) from exc


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_recording(file: UploadFile) -> TranscribeResponse:
    content_type = file.content_type or ""
    data = await file.read()
    return await transcribe(data, content_type)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_report(
    context: str = Form(...),
    before: list[UploadFile] = File(default_factory=list),
    after: list[UploadFile] = File(default_factory=list),
    connector: AiConnector = Depends(get_ai_connector),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    parsed_context = _parse_json_field(context, AnalyzeContextRequest)

    if len(before) != len(after):
        raise ApiError(
            status=422,
            type="photos-not-paired",
            title="Unprocessable Entity",
            detail="Before and after photos must be uploaded in equal counts.",
        )

    image_pairs: list[tuple[bytes, str, bytes, str]] = []
    for before_file, after_file in zip(before, after, strict=True):
        image_pairs.append(
            (
                await before_file.read(),
                before_file.content_type or "image/jpeg",
                await after_file.read(),
                after_file.content_type or "image/jpeg",
            )
        )

    return await analyze(
        context=parsed_context,
        image_pairs=image_pairs,
        connector=connector,
        settings=settings,
    )


@router.post("/check-pdf")
async def check_pdf(
    context: str = Form(...),
    signature: UploadFile = File(...),
) -> Response:
    parsed_context = _parse_json_field(context, CheckPdfContextRequest)
    if (signature.content_type or "") != "image/png":
        raise ApiError(
            status=422,
            type="signature-invalid",
            title="Unprocessable Entity",
            detail="The signature must be a PNG image.",
        )
    signature_png = await signature.read()
    pdf_bytes = await render_check_pdf(parsed_context, signature_png)
    return Response(content=pdf_bytes, media_type="application/pdf")
