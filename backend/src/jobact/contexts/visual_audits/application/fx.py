"""The local, deliberately dated FX snapshot a visual audit is priced against.

Kept alongside the visual-audit context because the stated price is only
ever converted for the auditor's price assessment -- nothing else in the
system reasons about currency conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


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
