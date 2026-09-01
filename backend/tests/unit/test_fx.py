"""Tests for the shared, deterministic FX conversion used by both the
visual auditor (USD-denominated price assessment) and report pricing
(converting the deterministic USD base amount into a revision's
snapshotted currency).
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

from jobact.shared.application.fx import convert_usd_cents

RATE = Decimal("84.4635")


def test_convert_usd_cents_is_a_passthrough_for_usd() -> None:
    assert convert_usd_cents(1_500, "USD", RATE) == 1_500


def test_convert_usd_cents_is_case_insensitive_for_usd() -> None:
    assert convert_usd_cents(1_500, "usd", RATE) == 1_500


def test_convert_usd_cents_converts_to_rub_at_the_configured_rate() -> None:
    expected = int((Decimal(1_500) * RATE).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    result = convert_usd_cents(1_500, "RUB", RATE)

    assert result == expected
    assert result == 126_695


def test_convert_usd_cents_preserves_none_as_no_suggestion() -> None:
    assert convert_usd_cents(None, "USD", RATE) is None
    assert convert_usd_cents(None, "RUB", RATE) is None


def test_convert_usd_cents_rejects_unsupported_currency() -> None:
    with pytest.raises(ValueError):
        convert_usd_cents(1_500, "EUR", RATE)
