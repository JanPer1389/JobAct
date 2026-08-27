from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from jobact.contexts.visual_audits.domain.events import VisualAuditRequested
from jobact.contexts.visual_audits.domain.visual_audit import (
    PhotoPair,
    VisualAuditAttempt,
    VisualAuditStateError,
    VisualAuditValidationError,
)


def _attempt(pair_count: int = 1) -> VisualAuditAttempt:
    return VisualAuditAttempt.request(
        id=uuid4(), organization_id=uuid4(), report_id=uuid4(), report_revision_id=uuid4(), visit_id=uuid4(),
        photo_pairs=[PhotoPair(uuid4(), uuid4()) for _ in range(pair_count)], work_description="Replaced the damaged valve and verified operation.",
        amount_cents=10000, currency="RUB", provided_price_usd=Decimal("118.39"), usd_rub_rate=Decimal("84.4635"),
        usd_rub_rate_date=date(2026, 8, 26), usd_rub_rate_source="CBR", created_at=datetime.now(UTC),
    )


def test_request_emits_event_and_enforces_pair_count() -> None:
    attempt = _attempt(2)
    assert attempt.status == "pending"
    assert isinstance(attempt.pull_events()[0], VisualAuditRequested)
    with pytest.raises(VisualAuditValidationError):
        _attempt(7)


def test_forward_only_completion_and_no_result_replacement() -> None:
    attempt = _attempt()
    now = datetime.now(UTC)
    attempt.start(now=now)
    attempt.succeed(result={"verdict": "high_quality"}, model="claude", prompt_tokens=1, completion_tokens=1, cost_usd=None, latency_ms=3, now=now)
    with pytest.raises(VisualAuditStateError):
        attempt.succeed(result={}, model="other", prompt_tokens=0, completion_tokens=0, cost_usd=None, latency_ms=0, now=now)


def test_acknowledgement_must_match_revision() -> None:
    attempt = _attempt()
    with pytest.raises(VisualAuditStateError):
        attempt.acknowledge(reason="continued_without_result", user_id=uuid4(), current_revision_id=uuid4(), now=datetime.now(UTC))
    with pytest.raises(VisualAuditStateError):
        attempt.acknowledge(reason="continued_without_result", user_id=uuid4(), current_revision_id=attempt.report_revision_id, now=datetime.now(UTC))
    attempt.start(now=datetime.now(UTC))
    attempt.fail(failure_code="provider_failed", latency_ms=1, now=datetime.now(UTC))
    attempt.acknowledge(reason="continued_without_result", user_id=uuid4(), current_revision_id=attempt.report_revision_id, now=datetime.now(UTC))
    assert attempt.is_acknowledged_for(attempt.report_revision_id)
    with pytest.raises(VisualAuditStateError):
        attempt.acknowledge(reason="continued_without_result", user_id=uuid4(), current_revision_id=attempt.report_revision_id, now=datetime.now(UTC))
