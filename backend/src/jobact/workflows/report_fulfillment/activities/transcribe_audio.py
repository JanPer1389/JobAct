from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from jobact.shared.application.ports import (
    AudioInspector,
    Clock,
    IdGenerator,
    ObjectStorage,
    SpeechTranscriber,
)
from jobact.workflows.report_fulfillment.failures import (
    AUDIO_INVALID,
    AUDIO_TOO_LARGE,
    AUDIO_TOO_LONG,
    TRANSCRIPTION_EMPTY,
    TRANSCRIPTION_UNAVAILABLE,
)

MAX_AUDIO_BYTES = 25 * 1024 * 1024
CLAIM_LEASE_SECONDS = 120
CLAIM_HEARTBEAT_SECONDS = 30
MAX_TRANSCRIPT_CHARS = 20_000

logger = logging.getLogger(__name__)


class AudioInvalidError(Exception):
    pass


class AudioTooLongError(Exception):
    pass


class TranscriptionUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class ClaimedTranscription:
    run_id: UUID
    report_id: UUID
    organization_id: UUID
    visit_id: UUID
    media_asset_id: UUID
    storage_key: str
    content_type: str
    byte_size: int
    correlation_id: UUID


class TranscriptionStore(Protocol):
    async def claim_transcription(
        self,
        *,
        report_id: UUID,
        run_id: UUID,
        now: datetime,
        lease_seconds: int,
    ) -> ClaimedTranscription | None: ...

    async def complete_transcription(
        self,
        *,
        run_id: UUID,
        report_id: UUID,
        transcript: str,
        detected_language: str | None,
        step_metadata: dict[str, object],
        started_at: datetime,
        finished_at: datetime,
        step_id: UUID,
    ) -> None: ...

    async def fail_transcription(
        self,
        *,
        run_id: UUID,
        report_id: UUID,
        error_code: str,
        started_at: datetime,
        finished_at: datetime,
        step_id: UUID,
    ) -> None: ...

    async def heartbeat_transcription(
        self, *, run_id: UUID, now: datetime
    ) -> None: ...


class TranscribeAudioActivity:
    def __init__(
        self,
        *,
        store: TranscriptionStore,
        object_storage: ObjectStorage,
        audio_inspector: AudioInspector,
        speech_transcriber: SpeechTranscriber,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._store = store
        self._object_storage = object_storage
        self._audio_inspector = audio_inspector
        self._speech_transcriber = speech_transcriber
        self._clock = clock
        self._id_generator = id_generator

    async def run(self, *, report_id: UUID, run_id: UUID) -> None:
        started_at = self._clock.now()
        try:
            claim = await self._store.claim_transcription(
                report_id=report_id,
                run_id=run_id,
                now=started_at,
                lease_seconds=CLAIM_LEASE_SECONDS,
            )
        except AudioInvalidError:
            await self._record_failure(report_id, run_id, AUDIO_INVALID, started_at)
            return
        if claim is None:
            return

        logger.info(
            "transcription_started report_id=%s run_id=%s media_asset_id=%s "
            "correlation_id=%s",
            report_id,
            run_id,
            claim.media_asset_id,
            claim.correlation_id,
        )
        failure_code: str | None = None
        try:
            if claim.byte_size > MAX_AUDIO_BYTES:
                failure_code = AUDIO_TOO_LARGE
            else:
                audio = await self._object_storage.download(claim.storage_key)
                if not audio or len(audio) != claim.byte_size:
                    raise AudioInvalidError
                inspection = await self._audio_inspector.inspect(
                    audio, claim.content_type
                )
                transcription = await self._transcribe_with_heartbeat(
                    audio, claim.content_type, run_id
                )
                transcript = transcription.text.strip()
                if (
                    not transcript
                    or len(transcript) < 20
                    or len(transcript) > MAX_TRANSCRIPT_CHARS
                ):
                    failure_code = TRANSCRIPTION_EMPTY
                else:
                    await self._store.complete_transcription(
                        run_id=run_id,
                        report_id=report_id,
                        transcript=transcript,
                        detected_language=transcription.language,
                        step_metadata={
                            "container": inspection.container,
                            "codec": inspection.codec,
                            "duration_seconds": inspection.duration_seconds,
                            "transcript_chars": len(transcript),
                            "detected_language": transcription.language,
                        },
                        started_at=started_at,
                        finished_at=self._clock.now(),
                        step_id=self._id_generator.new_id(),
                    )
                    logger.info(
                        "transcription_succeeded report_id=%s run_id=%s "
                        "media_asset_id=%s transcript_chars=%s language=%s "
                        "correlation_id=%s",
                        report_id,
                        run_id,
                        claim.media_asset_id,
                        len(transcript),
                        transcription.language,
                        claim.correlation_id,
                    )
                    return
        except AudioTooLongError:
            failure_code = AUDIO_TOO_LONG
        except AudioInvalidError:
            failure_code = AUDIO_INVALID
        except TranscriptionUnavailableError:
            failure_code = TRANSCRIPTION_UNAVAILABLE
        except Exception as exc:  # noqa: BLE001 - sanitize the external boundary
            logger.warning(
                "transcription_external_failure report_id=%s run_id=%s "
                "error_type=%s correlation_id=%s",
                report_id,
                run_id,
                type(exc).__name__,
                claim.correlation_id,
            )
            failure_code = TRANSCRIPTION_UNAVAILABLE

        assert failure_code is not None
        await self._record_failure(report_id, run_id, failure_code, started_at)

    async def _transcribe_with_heartbeat(
        self, audio: bytes, content_type: str, run_id: UUID
    ):
        task = asyncio.create_task(
            self._speech_transcriber.transcribe(audio, content_type)
        )
        try:
            while True:
                done, _ = await asyncio.wait({task}, timeout=CLAIM_HEARTBEAT_SECONDS)
                if task in done:
                    return task.result()
                await self._store.heartbeat_transcription(
                    run_id=run_id, now=self._clock.now()
                )
        finally:
            if not task.done():
                task.cancel()

    async def _record_failure(
        self, report_id: UUID, run_id: UUID, error_code: str, started_at: datetime
    ) -> None:
        await self._store.fail_transcription(
            run_id=run_id,
            report_id=report_id,
            error_code=error_code,
            started_at=started_at,
            finished_at=self._clock.now(),
            step_id=self._id_generator.new_id(),
        )
        logger.warning(
            "transcription_failed report_id=%s run_id=%s error_code=%s",
            report_id,
            run_id,
            error_code,
        )
