from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobact.contexts.reports.domain.report import Report, ReportStateError


def make_draft() -> Report:
    return Report.create_draft(
        id=uuid4(),
        organization_id=uuid4(),
        visit_id=uuid4(),
        human_id="JA-2026-0001",
        revision_id=uuid4(),
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
        created_by=uuid4(),
    )


def test_report_state_machine_enforces_signing_and_revision_invariants() -> None:
    report = make_draft()
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)

    with pytest.raises(ReportStateError):
        report.sign(
            signer_name="Ada Lovelace",
            signature_media_asset_id=uuid4(),
            ip="127.0.0.1",
            user_agent="pytest",
            now=now,
        )

    with pytest.raises(ReportStateError):
        report.mark_ready_for_signature(now=now)

    report.confirm(now=now)
    report.mark_ready_for_signature(now=now)

    with pytest.raises(ReportStateError):
        report.sign(
            signer_name="Ada Lovelace",
            signature_media_asset_id=None,
            ip="127.0.0.1",
            user_agent="pytest",
            now=now,
        )

    report.sign(
        signer_name="Ada Lovelace",
        signature_media_asset_id=uuid4(),
        ip="127.0.0.1",
        user_agent="pytest",
        now=now,
    )

    assert report.status == "signed"
    assert report.signed_at == now
    assert report.signatures[0].signed_at == now

    with pytest.raises(ReportStateError):
        report.update_revision(work_completed="A completed repair", amount_cents=12500)


def test_low_confidence_ai_draft_does_not_preserve_an_amount() -> None:
    report = make_draft()

    report.apply_ai_draft(
        work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
        materials=[],
        amount_cents=12_500,
        currency="RUB",
        ai_confidence="low",
    )

    assert report.current_revision.amount_cents is None
