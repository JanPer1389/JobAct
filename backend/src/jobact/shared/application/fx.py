"""The local, deliberately dated FX snapshot the system prices against.

One mechanism, shared by the two callers that need it: the visual auditor,
which reasons about a stated price in USD, and report pricing, which
converts a deterministic USD base amount into the currency snapshotted on
the report revision. The rate itself comes from `Settings`
(`usd_rub_rate`/`usd_rub_rate_date`/`usd_rub_rate_source`) and never from a
network call or a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

SUPPORTED_CURRENCIES = frozenset({"USD", "RUB"})


@dataclass(frozen=True)
class LocalFxSnapshot:
    usd_rub_rate: Decimal
    effective_date: date
    source: str


def provided_price_usd(
    amount_cents: int | None, currency: str, usd_rub_rate: Decimal
) -> Decimal | None:
    if amount_cents is None:
        return None
    amount = Decimal(amount_cents) / Decimal(100)
    if currency.upper() == "USD":
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if currency.upper() == "RUB":
        return (amount / usd_rub_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return None


def convert_usd_cents(
    usd_cents: int | None, currency: str, usd_rub_rate: Decimal
) -> int | None:
    """Convert USD minor units into the minor units of `currency`.

    `None` in, `None` out -- "no suggestion" survives conversion rather than
    becoming a free job. Unlike `provided_price_usd`, an unsupported currency
    raises instead of returning `None`: silently dropping a computed price
    would let a report reach a human with no amount at all.
    """
    if usd_cents is None:
        return None
    code = currency.upper()
    if code == "USD":
        return usd_cents
    if code == "RUB":
        return int(
            (Decimal(usd_cents) * usd_rub_rate).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
    raise ValueError(f"Unsupported currency: {currency!r}")
