"""Router-level tests for `/api/v1/demo/*`: multipart parsing, dependency
wiring, and the `ApiError` -> JSON envelope path. The AI/STT behavior
itself is covered by `test_demo_service.py`; here the demo-service
functions are monkeypatched at the router's own import so these tests
stay fast and network-free while still exercising the real FastAPI app.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from jobact.apps.api import demo_service
from jobact.apps.api.main import create_app
from jobact.apps.api.routers import demo as demo_router
from jobact.contracts.errors.v1.envelope import ApiError
from jobact.contracts.http.v1.demo import (
    AnalyzeResponse,
    MaterialDto,
    TranscribeResponse,
)
from jobact.contracts.http.v1.visual_audits import (
    Comparison,
    EvidenceItem,
    FairPriceRangeUsd,
    PriceAssessment,
    QualityAssessment,
    VisualAuditResult,
)


class _FakeConnector:
    provider_name = "qwen"


@pytest.fixture
def client() -> TestClient:
    # `Depends(get_ai_connector)` in the router binds the function object
    # imported from `demo_service` -- `dependency_overrides` matches by
    # that object identity, not by name, so this is the actual override
    # mechanism FastAPI provides (a plain monkeypatch of the router
    # module's name would not affect an already-defined `Depends(...)`).
    app = create_app()
    app.dependency_overrides[demo_service.get_ai_connector] = lambda: _FakeConnector()
    return TestClient(app)


def test_transcribe_endpoint_returns_the_transcript(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_transcribe(data: bytes, content_type: str) -> TranscribeResponse:
        assert content_type == "audio/webm"
        return TranscribeResponse(
            transcript="Replaced the leaking valve.",
            detected_language="ru",
            duration_seconds=8.0,
        )

    monkeypatch.setattr(demo_router, "transcribe", fake_transcribe)

    response = client.post(
        "/api/v1/demo/transcribe",
        files={"file": ("note.webm", b"fake-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "Replaced the leaking valve."


def test_analyze_endpoint_rejects_unpaired_photos(client: TestClient) -> None:
    context = {
        "raw_notes": "Replaced the leaking valve under the sink and tested the line.",
        "customer_name": "Ada Lovelace",
        "customer_address": "12 Analytical Engine Way",
        "customer_service_type": "Plumbing",
        "currency": "RUB",
        "locale": "ru-RU",
    }

    response = client.post(
        "/api/v1/demo/analyze",
        data={"context": json.dumps(context)},
        files=[("before", ("b1.jpg", b"before-bytes", "image/jpeg"))],
    )

    assert response.status_code == 422
    assert response.json()["type"] == "photos-not-paired"


def test_analyze_endpoint_returns_the_structured_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_analyze(*, context, image_pairs, connector, settings) -> AnalyzeResponse:
        assert len(image_pairs) == 1
        return AnalyzeResponse(
            work_completed="Replaced the leaking valve and tested the line.",
            materials=[MaterialDto(label="Valve", qty="1")],
            estimated_work_units=3,
            suggested_amount_cents=126_695,
            currency="RUB",
            confidence="high",
            visual_comparison=VisualAuditResult(
                verdict="high_quality",
                confidence=90,
                summary="Matches description.",
                comparison=Comparison(
                    visible_changes=["New valve"],
                    work_matches_description=True,
                    match_explanation="Clearly visible.",
                ),
                quality_assessment=QualityAssessment(
                    score=9, strengths=[], issues=[], unverified_items=[]
                ),
                price_assessment=PriceAssessment(
                    provided_price_usd=15.0,
                    fair_price_range_usd=FairPriceRangeUsd(min=10.0, max=20.0),
                    price_verdict="reasonable",
                    price_explanation="Reasonable.",
                ),
                evidence=[EvidenceItem(observation="New valve", impact="Confirms work")],
                limitations=[],
                recommended_next_steps=[],
            ),
        )

    monkeypatch.setattr(demo_router, "analyze", fake_analyze)

    context = {
        "raw_notes": "Replaced the leaking valve under the sink and tested the line.",
        "customer_name": "Ada Lovelace",
        "customer_address": "12 Analytical Engine Way",
        "customer_service_type": "Plumbing",
        "currency": "RUB",
        "locale": "ru-RU",
    }
    response = client.post(
        "/api/v1/demo/analyze",
        data={"context": json.dumps(context)},
        files=[
            ("before", ("b1.jpg", b"before-bytes", "image/jpeg")),
            ("after", ("a1.jpg", b"after-bytes", "image/jpeg")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_amount_cents"] == 126_695
    assert body["visual_comparison"]["verdict"] == "high_quality"


def test_analyze_endpoint_maps_api_error_to_the_error_envelope(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_analyze(**kwargs):
        raise ApiError(
            status=409,
            type="evidence-incomplete",
            title="Conflict",
            detail="At least one before/after photo pair is required.",
        )

    monkeypatch.setattr(demo_router, "analyze", failing_analyze)

    context = {
        "raw_notes": "Replaced the leaking valve under the sink and tested the line.",
        "customer_name": "Ada Lovelace",
        "customer_address": "12 Analytical Engine Way",
        "customer_service_type": "Plumbing",
    }
    response = client.post("/api/v1/demo/analyze", data={"context": json.dumps(context)})

    assert response.status_code == 409
    body = response.json()
    assert body["type"] == "evidence-incomplete"
    assert "correlation_id" in body


def test_check_pdf_endpoint_rejects_a_non_png_signature(client: TestClient) -> None:
    context = {
        "report_number": "JA-2026-0001",
        "customer_name": "Ada Lovelace",
        "customer_address": "12 Analytical Engine Way",
        "customer_phone": "+7 900 123-45-67",
        "customer_service_type": "Plumbing",
        "timestamp": "2026-08-28T10:00:00+00:00",
        "work_completed": "Replaced the leaking valve.",
        "signer_name": "Ada Lovelace",
    }

    response = client.post(
        "/api/v1/demo/check-pdf",
        data={"context": json.dumps(context)},
        files={"signature": ("sig.jpg", b"not-a-png", "image/jpeg")},
    )

    assert response.status_code == 422
    assert response.json()["type"] == "signature-invalid"
