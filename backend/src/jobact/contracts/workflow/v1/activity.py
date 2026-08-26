"""Minimal, framework-free shapes for workflow activities.

Concrete activities (drafting, PDF generation -- Task 4.4/4.5) define
their own specific input/output DTOs; this module only holds what's
generic across every activity: how a failure is reported back to the
runner without leaking anything unsafe into `workflow_runs.last_error`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityError:
    """A sanitized activity failure -- `detail` must never contain raw
    exception args, stack traces, secrets, or PII; it's stored verbatim
    in `workflow_runs.last_error`, which later tasks may expose to
    users (e.g. "why is my report stuck").
    """

    error_type: str
    detail: str
