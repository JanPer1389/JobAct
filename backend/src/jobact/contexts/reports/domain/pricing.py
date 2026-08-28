"""Deterministic pricing for an AI-suggested work amount.

The drafting model returns a count of materially distinct work units; turning
that count into money is this module's arithmetic and never the model's --
see `workflows/report_fulfillment/agent.py`'s `DraftedReport`, which has no
field for a price at all. Pure stdlib, so this stays inside the domain
layer's import rules (see `backend/CLAUDE.md`).
"""

from __future__ import annotations

from typing import Final

USD_CENTS_PER_WORK_UNIT: Final = 500
SUGGESTED_AMOUNT_CURRENCY: Final = "USD"


def suggested_amount_cents(estimated_work_units: int | None) -> int | None:
    """Convert a work-unit count into a suggested amount in USD cents.

    ``None`` means "no suggestion" -- e.g. the AI produced no unit count, or
    the deterministic template fallback ran because every provider failed.
    That is deliberately distinct from 0, which would assert a free job.
    """
    if estimated_work_units is None or estimated_work_units <= 0:
        return None
    return estimated_work_units * USD_CENTS_PER_WORK_UNIT
