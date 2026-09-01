"""HTTP DTOs for the stateless local-demo endpoints (`apps/api/routers/demo.py`).

The demo endpoints replace the durable, DB-backed report-fulfillment
workflow: there is no `Report`/`Visit`/`WorkflowRun` aggregate, no
persistence, and no polling. Each endpoint does one unit of protected
work (transcribe, draft+audit, render a PDF) and returns its result in
one response. These DTOs describe those responses; request bodies are
plain multipart form fields, not JSON, since every request carries file
bytes (audio, photos, or a signature).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from jobact.contracts.http.v1.visual_audits import VisualAuditResult

AppLocale = Literal["en-US", "ru-RU"]
AppCurrency = Literal["USD", "RUB"]


class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: str | None
    duration_seconds: float


class MaterialDto(BaseModel):
    label: str
    qty: str


class AnalyzeContextRequest(BaseModel):
    """The `context` multipart field of `POST /demo/analyze` -- everything
    the two AI calls need besides the before/after image files, which
    travel as separate multipart file parts.
    """

    raw_notes: str
    customer_name: str
    customer_address: str
    customer_service_type: str
    gps_lat: float | None = None
    gps_lon: float | None = None
    currency: AppCurrency = "RUB"
    locale: AppLocale = "ru-RU"

    @model_validator(mode="after")
    def validate_notes(self) -> AnalyzeContextRequest:
        self.raw_notes = self.raw_notes.strip()
        if not 20 <= len(self.raw_notes) <= 20_000:
            raise ValueError(
                "raw_notes must contain 20 to 20,000 non-whitespace characters."
            )
        return self


class AnalyzeResponse(BaseModel):
    work_completed: str
    materials: list[MaterialDto]
    estimated_work_units: int | None
    suggested_amount_cents: int | None = Field(
        default=None,
        description="`None` means the AI produced no suggestion; never assert a free job.",
    )
    currency: str
    confidence: Literal["high", "medium", "low"]
    visual_comparison: VisualAuditResult


class CheckPdfContextRequest(BaseModel):
    """The `context` multipart field of `POST /demo/check-pdf`."""

    report_number: str
    customer_name: str
    customer_address: str
    customer_phone: str
    customer_service_type: str
    timestamp: datetime
    gps_lat: float | None = None
    gps_lon: float | None = None
    work_completed: str
    materials: list[MaterialDto] = []
    amount_cents: int | None = None
    currency: AppCurrency = "RUB"
    signer_name: str
    locale: AppLocale = "ru-RU"
