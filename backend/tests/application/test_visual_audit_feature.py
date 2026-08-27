from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from jobact.contexts.reports.application.report_handlers import (
    _require_current_audit_acknowledgement,
)
from jobact.contexts.visual_audits.application import visual_audit_handlers as handlers
from jobact.contexts.visual_audits.application.visual_audit_handlers import (
    CreateVisualAuditHandler,
    LocalFxSnapshot,
)
from jobact.contexts.visual_audits.domain.visual_audit import VisualAuditStateError
from jobact.shared.application.authorization import AuthorizationError
from jobact.workflows.report_fulfillment.states import WorkflowState
from tests.fakes import FakeClock, FakeIdGenerator


class FakeUow:
    session = object()

    def __init__(self) -> None:
        self.registered = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def register(self, item) -> None:
        self.registered.append(item)


@pytest.mark.asyncio
async def test_create_handler_snapshots_valid_pairs_and_converts_rub(monkeypatch) -> None:
    organization_id, report_id, revision_id, visit_id = uuid4(), uuid4(), uuid4(), uuid4()
    before_id, after_id = uuid4(), uuid4()
    revision = SimpleNamespace(id=revision_id, work_completed="Replaced a damaged valve.", amount_cents=10_000, currency="RUB", confirmed_by_user_at=datetime.now(UTC), amount_confirmed_at=datetime.now(UTC))
    report = SimpleNamespace(id=report_id, organization_id=organization_id, visit_id=visit_id, status="draft", current_revision=revision)
    assets = {
        before_id: SimpleNamespace(id=before_id, organization_id=organization_id, status="attached", kind="photo", phase="before", visit_id=visit_id, content_type="image/jpeg"),
        after_id: SimpleNamespace(id=after_id, organization_id=organization_id, status="attached", kind="photo", phase="after", visit_id=visit_id, content_type="image/jpeg"),
    }
    captured = []

    class Reports:
        def __init__(self, session): pass
        async def get_by_id(self, value): return report
    class Runs:
        def __init__(self, session): pass
        async def get_by_subject(self, value): return SimpleNamespace(organization_id=organization_id, state=WorkflowState.REVIEW_PENDING)
    class Media:
        def __init__(self, session): pass
        async def get_by_id(self, value): return assets.get(value)
    class Audits:
        def __init__(self, session): pass
        async def add(self, value): captured.append(value)

    monkeypatch.setattr(handlers, "ReportRepository", Reports)
    monkeypatch.setattr(handlers, "WorkflowRunRepository", Runs)
    monkeypatch.setattr(handlers, "MediaAssetRepository", Media)
    monkeypatch.setattr(handlers, "VisualAuditRepository", Audits)
    attempt = await CreateVisualAuditHandler(
        FakeUow(), FakeClock(datetime(2026, 8, 27, tzinfo=UTC)), FakeIdGenerator(),
        LocalFxSnapshot(Decimal("84.4635"), date(2026, 8, 26), "CBR"),
    ).handle(organization_id=organization_id, report_id=report_id, before_photo_asset_ids=[before_id], after_photo_asset_ids=[after_id])
    assert captured == [attempt]
    assert attempt.provided_price_usd == Decimal("1.18")
    assert attempt.photo_pairs[0].before_asset_id == before_id


@pytest.mark.asyncio
async def test_create_handler_rejects_cross_tenant_report(monkeypatch) -> None:
    class Reports:
        def __init__(self, session): pass
        async def get_by_id(self, value): return SimpleNamespace(organization_id=uuid4())
    monkeypatch.setattr(handlers, "ReportRepository", Reports)
    with pytest.raises(AuthorizationError):
        await CreateVisualAuditHandler(FakeUow(), FakeClock(), FakeIdGenerator(), LocalFxSnapshot(Decimal("84.4635"), date(2026, 8, 26), "CBR")).handle(
            organization_id=uuid4(), report_id=uuid4(), before_photo_asset_ids=[uuid4()], after_photo_asset_ids=[uuid4()]
        )


def test_signature_guard_accepts_only_matching_acknowledged_snapshot() -> None:
    revision = SimpleNamespace(id=uuid4(), work_completed="Done", amount_cents=100, currency="RUB")
    report = SimpleNamespace(current_revision=revision)
    audit = SimpleNamespace(
        work_description="Done", amount_cents=100, currency="RUB",
        is_acknowledged_for=lambda revision_id: revision_id == revision.id,
    )
    _require_current_audit_acknowledgement(report, audit)
    audit.work_description = "Old description"
    with pytest.raises(VisualAuditStateError):
        _require_current_audit_acknowledgement(report, audit)


def test_worker_registers_visual_audit_handler() -> None:
    from jobact.apps.worker.__main__ import HANDLER_REGISTRY
    assert "VisualAuditRequested" in HANDLER_REGISTRY
