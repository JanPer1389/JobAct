from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.uow import UnitOfWork
from jobact.shared.infrastructure.postgres.uow import SqlAlchemyUnitOfWork
from jobact.workflows.report_fulfillment.activities.transcribe_audio import (
    AudioInvalidError,
    ClaimedTranscription,
)
from jobact.workflows.report_fulfillment.repository import (
    WorkflowConcurrencyError,
    WorkflowRunRepository,
)
from jobact.workflows.report_fulfillment.states import WorkflowState
from jobact.workflows.report_fulfillment.step_repository import WorkflowStepRepository

_STEP_NAME = "transcribe_audio"


class PostgresTranscriptionStore:
    def __init__(
        self, uow_factory: Callable[[], UnitOfWork] = SqlAlchemyUnitOfWork
    ) -> None:
        self._uow_factory = uow_factory

    async def claim_transcription(
        self,
        *,
        report_id: UUID,
        run_id: UUID,
        now: datetime,
        lease_seconds: int,
    ) -> ClaimedTranscription | None:
        async with self._uow_factory() as uow:
            run_repo = WorkflowRunRepository(uow.session)
            run = await run_repo.get_by_id(run_id)
            if (
                run is None
                or run.workflow_type != "report_fulfillment"
                or run.subject_id != report_id
                or run.state != WorkflowState.TRANSCRIPTION_PENDING
                or (run.next_retry_at is not None and run.next_retry_at > now)
                or not run.can_claim(now=now, lease_seconds=lease_seconds)
            ):
                return None

            expected_version = run.state_version
            run.claim_attempt(now=now)
            try:
                await run_repo.save(run, expected_version=expected_version)
            except WorkflowConcurrencyError:
                return None

            report = await ReportRepository(uow.session).get_by_id(report_id)
            transcription_input = run.input_data.get("transcription")
            media_asset_id = (
                transcription_input.get("media_asset_id")
                if isinstance(transcription_input, dict)
                else None
            )
            if report is None or not isinstance(media_asset_id, str):
                raise AudioInvalidError
            visit = await VisitRepository(uow.session).get_by_id(report.visit_id)
            try:
                asset_id = UUID(media_asset_id)
            except ValueError as exc:
                raise AudioInvalidError from exc
            asset = await MediaAssetRepository(uow.session).get_by_id(asset_id)
            if (
                report.organization_id != run.organization_id
                or visit is None
                or visit.organization_id != run.organization_id
                or report.visit_id != visit.id
                or asset is None
                or asset.organization_id != run.organization_id
                or asset.visit_id != visit.id
                or asset.id != asset_id
                or asset.kind != "audio"
                or asset.status != "attached"
                or asset.content_type not in {"audio/webm", "audio/mp4"}
            ):
                raise AudioInvalidError

            return ClaimedTranscription(
                run_id=run.id,
                report_id=report.id,
                organization_id=run.organization_id,
                visit_id=visit.id,
                media_asset_id=asset.id,
                storage_key=asset.storage_key,
                content_type=asset.content_type,
                byte_size=asset.byte_size,
                correlation_id=run.correlation_id,
            )

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
    ) -> None:
        async with self._uow_factory() as uow:
            run_repo = WorkflowRunRepository(uow.session)
            run = await run_repo.get_by_id(run_id)
            report = await ReportRepository(uow.session).get_by_id(report_id)
            if (
                run is None
                or report is None
                or run.subject_id != report_id
                or run.organization_id != report.organization_id
                or run.state != WorkflowState.TRANSCRIPTION_PENDING
                or run.claimed_at is None
            ):
                raise AudioInvalidError
            visit_repo = VisitRepository(uow.session)
            visit = await visit_repo.get_by_id(report.visit_id)
            if visit is None or visit.organization_id != run.organization_id:
                raise AudioInvalidError

            expected_version = run.state_version
            visit.update_capture_state(raw_notes=transcript)
            await visit_repo.save(visit)
            transcription_input = dict(run.input_data.get("transcription") or {})
            transcription_input.update(
                {"transcript": transcript, "detected_language": detected_language}
            )
            run.input_data = {
                **run.input_data,
                "transcription": transcription_input,
                "drafting": {"raw_notes": transcript},
            }
            run.record_step_success()
            run.transition_to(WorkflowState.DRAFTING_PENDING)
            run.request_dispatch()
            await run_repo.save(run, expected_version=expected_version)
            await WorkflowStepRepository(uow.session).record(
                id=step_id,
                run_id=run.id,
                step=_STEP_NAME,
                status="succeeded",
                attempt=run.attempt,
                input_data=None,
                output_data=step_metadata,
                error=None,
                started_at=started_at,
                finished_at=finished_at,
            )
            uow.register(run)

    async def fail_transcription(
        self,
        *,
        run_id: UUID,
        report_id: UUID,
        error_code: str,
        started_at: datetime,
        finished_at: datetime,
        step_id: UUID,
    ) -> None:
        async with self._uow_factory() as uow:
            run_repo = WorkflowRunRepository(uow.session)
            run = await run_repo.get_by_id(run_id)
            if (
                run is None
                or run.subject_id != report_id
                or run.state != WorkflowState.TRANSCRIPTION_PENDING
            ):
                return
            expected_version = run.state_version
            run.record_failure(error=error_code, now=finished_at, max_attempts=3)
            if run.state == WorkflowState.TRANSCRIPTION_PENDING:
                run.request_dispatch()
            await run_repo.save(run, expected_version=expected_version)
            await WorkflowStepRepository(uow.session).record(
                id=step_id,
                run_id=run.id,
                step=_STEP_NAME,
                status="failed",
                attempt=run.attempt,
                input_data=None,
                output_data={"error_code": error_code},
                error=error_code,
                started_at=started_at,
                finished_at=finished_at,
            )
            uow.register(run)

    async def heartbeat_transcription(self, *, run_id: UUID, now: datetime) -> None:
        async with self._uow_factory() as uow:
            run_repo = WorkflowRunRepository(uow.session)
            run = await run_repo.get_by_id(run_id)
            if (
                run is None
                or run.state != WorkflowState.TRANSCRIPTION_PENDING
                or run.claimed_at is None
            ):
                return
            expected_version = run.state_version
            run.claimed_at = now
            run.state_version += 1
            try:
                await run_repo.save(run, expected_version=expected_version)
            except WorkflowConcurrencyError:
                return
