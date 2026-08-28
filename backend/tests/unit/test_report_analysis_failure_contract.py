from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from jobact.workflows.report_fulfillment.activities.run_report_analysis import (
    RunReportAnalysisActivity,
)
from jobact.workflows.report_fulfillment.failures import (
    AI_ANALYSIS_TIMEOUT,
    AI_PROVIDERS_UNAVAILABLE,
    classify_analysis_failures,
)
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState


def _run() -> WorkflowRun:
    return WorkflowRun.start(
        id=uuid4(),
        organization_id=uuid4(),
        workflow_type="report_fulfillment",
        subject_id=uuid4(),
        correlation_id=uuid4(),
        initial_state=WorkflowState.DRAFTING_PENDING,
    )


def test_all_provider_timeouts_are_a_terminal_504_failure() -> None:
    failure = classify_analysis_failures([TimeoutError(), TimeoutError()])

    assert failure.code == AI_ANALYSIS_TIMEOUT
    assert failure.http_status == 504
    assert failure.retryable is True


def test_provider_error_or_empty_result_is_a_terminal_502_failure() -> None:
    failure = classify_analysis_failures([TimeoutError(), ValueError("empty")])

    assert failure.code == AI_PROVIDERS_UNAVAILABLE
    assert failure.http_status == 502
    assert failure.retryable is True


def test_ai_failure_moves_run_to_failed_and_can_be_retried() -> None:
    run = _run()

    run.fail(
        code=AI_ANALYSIS_TIMEOUT,
        now=datetime(2026, 8, 28, tzinfo=UTC),
    )

    assert run.state == WorkflowState.FAILED
    assert run.last_error == AI_ANALYSIS_TIMEOUT
    run.resume_to(WorkflowState.DRAFTING_PENDING)
    assert run.state == WorkflowState.DRAFTING_PENDING
    assert run.last_error is None


class _Connector:
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name


async def test_analysis_fails_over_to_second_provider_for_the_whole_saga() -> None:
    calls: list[tuple[str, str]] = []

    class _Draft:
        work_completed = "Completed"
        estimated_work_units = 2

    class _DraftResult:
        draft = _Draft()
        model = "secondary-model"

    class _AuditResult:
        model = "secondary-model"

    async def draft(connector, context):
        calls.append((connector.provider_name, "draft"))
        if connector.provider_name == "anthropic":
            raise TimeoutError()
        return _DraftResult()

    async def audit(connector, **kwargs):
        calls.append((connector.provider_name, "audit"))
        return _AuditResult()

    activity = RunReportAnalysisActivity(
        uow=None,
        connector=None,
        connectors=[_Connector("anthropic"), _Connector("openrouter")],
        object_storage=None,
        clock=None,
        id_generator=None,
        fx=SimpleNamespace(usd_rub_rate=100),
        draft_report_fn=draft,
        run_visual_audit_fn=audit,
    )
    drafted, audit_result, failure, model = await activity._run_ai_steps(
        report_id=uuid4(),
        run_id=uuid4(),
        correlation_id=uuid4(),
        context=type(
            "Context",
            (),
            {
                "raw_notes": "Completed the repair and verified operation.",
                "customer_service_type": None,
                "gps_lat": None,
                "gps_lon": None,
                "response_language": "English",
            },
        )(),
        image_pairs=[(b"before", "image/jpeg", b"after", "image/jpeg")],
    )

    assert calls == [
        ("anthropic", "draft"),
        ("openrouter", "draft"),
        ("openrouter", "audit"),
    ]
    assert drafted.work_completed == "Completed"
    assert audit_result is not None
    assert failure is None
    assert model == "secondary-model"
