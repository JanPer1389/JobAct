from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from jobact.shared.infrastructure.clock import SystemClock
from jobact.shared.infrastructure.config import get_settings
from jobact.shared.infrastructure.id_generator import UuidIdGenerator
from jobact.shared.infrastructure.object_storage.s3_compatible import (
    S3CompatibleObjectStorage,
)
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.shared.infrastructure.stt.faster_whisper import FasterWhisperTranscriber
from jobact.shared.infrastructure.stt.pyav_inspector import PyAvAudioInspector
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    TranscribeAudioActivity,
)
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.transcription_store import (
    PostgresTranscriptionStore,
)

logger = logging.getLogger(__name__)
_TRANSCRIBER = FasterWhisperTranscriber()


async def process_transcription_event(payload: dict) -> None:
    inner = payload.get("payload") or {}
    if (
        payload.get("event_type") != "TranscriptionDispatchRequested"
        or inner.get("workflow_type") != "report_fulfillment"
    ):
        return
    not_before = inner.get("not_before")
    if isinstance(not_before, str):
        due_at = datetime.fromisoformat(not_before)
        delay = (due_at - datetime.now(UTC)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
    await run_transcription(UUID(inner["subject_id"]))


async def run_transcription(report_id: UUID) -> None:
    async with SqlAlchemyUnitOfWork() as uow:
        run = await WorkflowRunRepository(uow.session).get_by_subject(report_id)
    if run is None:
        logger.info("transcription_skipped report_id=%s", report_id)
        return
    settings = get_settings()
    activity = TranscribeAudioActivity(
        store=PostgresTranscriptionStore(),
        object_storage=S3CompatibleObjectStorage(settings),
        audio_inspector=PyAvAudioInspector(),
        speech_transcriber=_TRANSCRIBER,
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
    )
    await activity.run(report_id=report_id, run_id=run.id)
