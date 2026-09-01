"""Pure-function tests for `classify_analysis_failures`, extracted from
the old `RunReportAnalysisActivity`-backed contract test when the durable
workflow was removed in the local-demo downgrade. The classification
logic itself is unchanged and still drives `demo_service._analysis_failure`.
"""

from pydantic_ai.exceptions import ModelHTTPError

from jobact.workflows.report_fulfillment.failures import (
    AI_ANALYSIS_TIMEOUT,
    AI_PROVIDERS_UNAVAILABLE,
    classify_analysis_failures,
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


def test_all_provider_client_errors_require_configuration_change() -> None:
    failure = classify_analysis_failures(
        [
            ModelHTTPError(401, "qwen3.8-flash"),
            ModelHTTPError(403, "qwen3-vl-flash"),
        ]
    )

    assert failure.code == "AI_PROVIDER_CONFIGURATION_ERROR"
    assert failure.http_status == 503
    assert failure.retryable is False
