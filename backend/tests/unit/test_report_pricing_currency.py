"""`_apply_result` converts the deterministic USD base amount into the
report revision's snapshotted currency, and never mutates that currency
itself -- see `Report.apply_ai_unified_result`.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from jobact.contexts.reports.domain.report import Report
from jobact.workflows.report_fulfillment.activities.run_report_analysis import (
    _apply_result,
)
from jobact.workflows.report_fulfillment.agent import DraftedReport
from tests.fakes import FakeIdGenerator

RATE = Decimal("84.4635")


def _make_report(currency: str) -> Report:
    return Report.create_draft(
        id=uuid4(),
        organization_id=uuid4(),
        visit_id=uuid4(),
        human_id="JA-2026-0001",
        revision_id=uuid4(),
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
        created_by=uuid4(),
        currency=currency,
    )


def _drafted(units: int) -> DraftedReport:
    return DraftedReport(
        work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
        materials=[],
        estimated_work_units=units,
        confidence="high",
    )


def test_usd_report_gets_the_usd_base_amount() -> None:
    report = _make_report("USD")

    converted = _apply_result(
        report,
        _drafted(3),
        FakeIdGenerator(),
        currency="USD",
        usd_rub_rate=RATE,
        visual_comparison_status=None,
        visual_comparison=None,
    )

    assert converted == 1_500
    assert report.current_revision.amount_cents == 1_500
    assert report.current_revision.currency == "USD"


def test_rub_report_gets_the_same_estimate_converted_to_rub() -> None:
    report = _make_report("RUB")

    converted = _apply_result(
        report,
        _drafted(3),
        FakeIdGenerator(),
        currency="RUB",
        usd_rub_rate=RATE,
        visual_comparison_status=None,
        visual_comparison=None,
    )

    assert converted == 126_695
    assert report.current_revision.amount_cents == 126_695
    assert report.current_revision.currency == "RUB"


def test_no_unit_estimate_yields_no_suggestion_in_either_currency() -> None:
    report = _make_report("RUB")

    converted = _apply_result(
        report,
        DraftedReport(
            work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
            materials=[],
            estimated_work_units=None,
            confidence="low",
        ),
        FakeIdGenerator(),
        currency="RUB",
        usd_rub_rate=RATE,
        visual_comparison_status=None,
        visual_comparison=None,
    )

    assert converted is None
    assert report.current_revision.amount_cents is None


def test_response_language_maps_locale_independently_of_currency() -> None:
    """The AI's target response language follows the interface-language
    preference (`users.locale`), never the currency preference -- the two
    must be able to vary independently (e.g. Russian UI + USD pricing).
    """
    from jobact.workflows.report_fulfillment.activities.run_report_analysis import (
        _RESPONSE_LANGUAGE_BY_LOCALE,
    )

    assert _RESPONSE_LANGUAGE_BY_LOCALE["en-US"] == "English"
    assert _RESPONSE_LANGUAGE_BY_LOCALE["ru-RU"] == "Russian"
    # An unrecognised/missing locale must not raise -- default to English.
    assert _RESPONSE_LANGUAGE_BY_LOCALE.get("", "English") == "English"
