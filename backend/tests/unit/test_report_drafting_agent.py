import pytest
from pydantic import ValidationError

from jobact.workflows.report_fulfillment.agent import DraftedReport


def test_low_confidence_structured_output_rejects_a_proposed_amount() -> None:
    """Removing the safety validation would let an uncertain price reach a report."""
    with pytest.raises(ValidationError):
        DraftedReport(
            work_completed="Replaced the damaged kitchen sink drain and tested for leaks.",
            materials=[],
            amount_cents=12_500,
            confidence="low",
        )
