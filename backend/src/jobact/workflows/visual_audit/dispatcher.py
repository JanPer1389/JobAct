from __future__ import annotations

from uuid import UUID

from jobact.shared.application.ai_connectors import NoAiConnectorConfigured
from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.llm.connectors import build_ai_connector
from jobact.shared.infrastructure.object_storage.s3_compatible import (
    S3CompatibleObjectStorage,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.visual_audit.activity import RunVisualAuditActivity


async def process_visual_audit_event(payload: dict) -> None:
    settings = get_settings()
    try:
        connector = build_ai_connector(settings)
    except NoAiConnectorConfigured:
        connector = None
    activity = RunVisualAuditActivity(
        uow=SqlAlchemyUnitOfWork(), storage=S3CompatibleObjectStorage(settings),
        connector=connector, clock=SystemClock(),
    )
    await activity.run(UUID(payload["aggregate_id"]))
