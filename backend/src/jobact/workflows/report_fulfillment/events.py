"""Domain events emitted by `WorkflowRun`.

`WorkflowStepDispatchRequested` is how a workflow asks for its current
state's step to be executed asynchronously: the event is committed to
`platform.outbox` in the same transaction as the run itself, published
onto `outbox.WorkflowRun`, and consumed by `apps/worker`. That makes
dispatch durable across an API restart -- unlike an in-process
`asyncio.create_task`, which is lost with the process that scheduled it.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from jobact.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class WorkflowStepDispatchRequested(DomainEvent):
    organization_id: UUID
    workflow_type: str
    subject_id: UUID
    state: str
