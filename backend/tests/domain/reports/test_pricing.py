import pytest

from jobact.contexts.reports.domain.pricing import (
    SUGGESTED_AMOUNT_CURRENCY,
    USD_CENTS_PER_WORK_UNIT,
    suggested_amount_cents,
)


def test_usd_cents_per_work_unit_is_five_dollars() -> None:
    assert USD_CENTS_PER_WORK_UNIT == 500
    assert SUGGESTED_AMOUNT_CURRENCY == "USD"


@pytest.mark.parametrize(
    ("units", "expected_cents"),
    [(1, 500), (3, 1500), (7, 3500)],
)
def test_suggested_amount_cents_is_deterministic(units: int, expected_cents: int) -> None:
    assert suggested_amount_cents(units) == expected_cents


@pytest.mark.parametrize("units", [None, 0])
def test_no_unit_count_means_no_suggestion(units: int | None) -> None:
    assert suggested_amount_cents(units) is None
