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


def test_ai_draft_receives_the_suggested_amount_even_at_low_confidence() -> None:
    """The suggested amount pre-fills the field regardless of confidence --
    confidence is advisory metadata, not a gate on whether a price appears.
    """
    report = make_draft()

    report.apply_ai_unified_result(
        work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
        materials=[],
        amount_cents=1_500,
        currency="USD",
        ai_confidence="low",
    )

    assert report.current_revision.amount_cents == 1_500
    assert report.current_revision.currency == "USD"
    assert report.current_revision.ai_confidence == "low"


def test_an_ai_suggested_amount_is_not_a_human_confirmation() -> None:
    """A suggested price must never itself count as the user confirming it."""
    report = make_draft()

    report.apply_ai_unified_result(
        work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
        materials=[],
        amount_cents=1_500,
        currency="USD",
        ai_confidence="high",
    )

    assert report.current_revision.confirmed_by_user_at is None
    assert report.current_revision.amount_confirmed_at is None
    with pytest.raises(ReportStateError):
        report.mark_ready_for_signature(now=datetime(2026, 8, 26, tzinfo=UTC))


def test_a_user_edit_replaces_the_ai_suggestion_and_is_what_gets_confirmed() -> None:
    """Editing a suggested amount must behave exactly like editing any other
    user-entered amount, and the edited value -- not the AI's -- is what a
    subsequent confirmation freezes.
    """
    report = make_draft()
    report.apply_ai_unified_result(
        work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
        materials=[],
        amount_cents=1_500,
        currency="USD",
        ai_confidence="medium",
    )

    report.update_revision(work_completed="Replaced the drain assembly.", amount_cents=9_900)

    assert report.current_revision.amount_cents == 9_900
    assert report.current_revision.source == "human"
    assert report.current_revision.confirmed_by_user_at is None
    assert report.current_revision.amount_confirmed_at is None

    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    report.confirm(now=now)
    report.mark_ready_for_signature(now=now)

    assert report.current_revision.amount_cents == 9_900
    assert report.current_revision.amount_confirmed_at == now
    assert report.current_revision.frozen_at == now
