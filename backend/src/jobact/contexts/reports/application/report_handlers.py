"""Report command/query handlers -- thin orchestration over
`UnitOfWork` + `ReportRepository`, same pattern as every other context.

`raw_notes` (the create-report input) is NOT read from
`visits.raw_notes` -- per this plan's own ruling, `POST /reports`'s
request body is the sole authoritative source for AI drafting input.
`raw_notes` is retained in the report-fulfillment workflow input so a
background drafting attempt and later manual recovery share the same
authoritative request input without adding it to the report revision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.domain.report import Material, Report, ReportStateError
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.application.ports import Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.report_fulfillment.repository import WorkflowRunRepository
from jobact.workflows.report_fulfillment.run import WorkflowRun
from jobact.workflows.report_fulfillment.states import WorkflowState


class ReportEvidenceIncompleteError(Exception):
    """A visit lacks the evidence AI analysis requires."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(
            "This visit is missing required evidence before analysis can start."
        )
        self.missing = missing


@dataclass(frozen=True)
class CreatedReport:
    report: Report
    workflow_run_id: UUID


class ManualRecoveryInput:
    def __init__(self, *, raw_notes: str, stage: Literal["analysis", "pdf"]) -> None:
        self.raw_notes = raw_notes
        self.stage = stage


class CreateReportHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        organization_id: UUID,
        visit_id: UUID,
        created_by: UUID,
        raw_notes: str,
        correlation_id: UUID | None = None,
    ) -> CreatedReport:
        async with self._uow:
            visit = await VisitRepository(self._uow.session).get_by_id(visit_id)
            if visit is None or visit.organization_id != organization_id:
                raise AuthorizationError(
                    f"Visit {visit_id} does not belong to organization {organization_id}."
                )

            media_repo = MediaAssetRepository(self._uow.session)
            before = await media_repo.list_attached_by_visit_and_phase(
                visit_id, "before"
            )
            after = await media_repo.list_attached_by_visit_and_phase(visit_id, "after")
            missing = visit.evidence_readiness(
                attached_before_count=len(before),
                attached_after_count=len(after),
            ).missing_requirements()
            if not raw_notes.strip():
                missing.append("raw_notes")
            if missing:
                raise ReportEvidenceIncompleteError(missing)

            repo = ReportRepository(self._uow.session)
            now = self._clock.now()
            human_id = await repo.allocate_human_id(organization_id, now.year)
            report = Report.create_draft(
                id=self._id_generator.new_id(),
                organization_id=organization_id,
                visit_id=visit_id,
                human_id=human_id,
                revision_id=self._id_generator.new_id(),
                created_at=now,
                created_by=created_by,
            )
            await repo.add(report)
            run = WorkflowRun.start(
                id=self._id_generator.new_id(),
                organization_id=organization_id,
                workflow_type="report_fulfillment",
                subject_id=report.id,
                correlation_id=correlation_id or self._id_generator.new_id(),
                initial_state=WorkflowState.DRAFTING_PENDING,
                input_data={"drafting": {"raw_notes": raw_notes}},
            )
            # Enqueued as an outbox row in this same transaction, so the
            # job survives an API restart -- see WorkflowRun.request_dispatch.
            run.request_dispatch()
            await WorkflowRunRepository(self._uow.session).add(run)
            self._uow.register(report)
            self._uow.register(run)
        return CreatedReport(report=report, workflow_run_id=run.id)


class GetReportHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, *, report_id: UUID, organization_id: UUID) -> Report:
        async with self._uow:
            report = await ReportRepository(self._uow.session).get_by_id(report_id)
        if report is None or report.organization_id != organization_id:
            raise AuthorizationError(
                f"Report {report_id} does not belong to organization {organization_id}."
            )
        return report


class GetReportManualRecoveryHandler:
    """Return drafting input only for the owning org's parked workflow."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(
        self, *, report_id: UUID, organization_id: UUID
    ) -> ManualRecoveryInput:
        async with self._uow:
            report = await ReportRepository(self._uow.session).get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(
                    f"Report {report_id} does not belong to organization {organization_id}."
                )

            run = await WorkflowRunRepository(self._uow.session).get_by_subject(report_id)
            if (
                run is None
                or run.organization_id != organization_id
                or run.workflow_type != "report_fulfillment"
                or run.state != WorkflowState.MANUAL_INPUT_REQUIRED
            ):
                raise AuthorizationError(
                    f"Manual recovery is unavailable for report {report_id}."
                )

            drafting_input = run.input_data.get("drafting")
            raw_notes = (
                drafting_input.get("raw_notes")
                if isinstance(drafting_input, dict)
                else None
            )
            if not isinstance(raw_notes, str):
                raise AuthorizationError(
                    f"Manual recovery is unavailable for report {report_id}."
                )
            stage: Literal["analysis", "pdf"] = (
                "pdf" if report.status == "signed" else "analysis"
            )

        return ManualRecoveryInput(raw_notes=raw_notes, stage=stage)


class ListReportsHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, *, organization_id: UUID) -> list[Report]:
        async with self._uow:
            return await ReportRepository(self._uow.session).list_by_organization(
                organization_id
            )


class UpdateReportRevisionHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(
        self,
        *,
        report_id: UUID,
        organization_id: UUID,
        work_completed: str,
        amount_cents: int | None,
        currency: str,
        materials: list[Material],
    ) -> Report:
        async with self._uow:
            repo = ReportRepository(self._uow.session)
            report = await repo.get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(
                    f"Report {report_id} does not belong to organization {organization_id}."
                )
            report.update_revision(
                work_completed=work_completed,
                amount_cents=amount_cents,
                currency=currency,
                materials=materials,
            )
            await repo.save(report)
            self._uow.register(report)

            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_subject(report_id)
            if run is not None and run.state == WorkflowState.MANUAL_INPUT_REQUIRED:
                if (
                    run.organization_id != organization_id
                    or run.workflow_type != "report_fulfillment"
                ):
                    raise AuthorizationError(
                        f"Workflow for report {report_id} does not belong to "
                        f"organization {organization_id}."
                    )
                expected_version = run.state_version
                run.resume_manual_review()
                await run_repo.save(run, expected_version=expected_version)
                self._uow.register(run)
        return report


class ConfirmReportHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def handle(self, *, report_id: UUID, organization_id: UUID) -> Report:
        return await _load_mutate_save(
            self._uow,
            report_id,
            organization_id,
            lambda report: report.confirm(now=self._clock.now()),
        )


class ReadyForSignatureHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def handle(self, *, report_id: UUID, organization_id: UUID) -> Report:
        async with self._uow:
            report_repo = ReportRepository(self._uow.session)
            report = await report_repo.get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(
                    f"Report {report_id} does not belong to organization {organization_id}."
                )
            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_subject(report_id)
            run = _authorize_report_workflow(run, report_id, organization_id)

            report.mark_ready_for_signature(now=self._clock.now())
            await report_repo.save(report)
            expected_version = run.state_version
            run.transition_to(WorkflowState.SIGNATURE_PENDING)
            await run_repo.save(run, expected_version=expected_version)
            self._uow.register(report)
            self._uow.register(run)
        return report


class SignReportHandler:
    def __init__(self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        report_id: UUID,
        organization_id: UUID,
        signer_name: str,
        signature_media_asset_id: UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> Report:
        async with self._uow:
            repo = ReportRepository(self._uow.session)
            report = await repo.get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(
                    f"Report {report_id} does not belong to organization {organization_id}."
                )

            asset = await MediaAssetRepository(self._uow.session).get_by_id(
                signature_media_asset_id
            )
            if (
                asset is None
                or asset.organization_id != organization_id
                or asset.kind != "signature"
                or asset.status != "attached"
            ):
                raise AuthorizationError(
                    "Signature media asset must be attached and belong to this organization."
                )

            report.sign(
                signer_name=signer_name,
                signature_media_asset_id=asset.id,
                signature_id=self._id_generator.new_id(),
                ip=ip,
                user_agent=user_agent,
                now=self._clock.now(),
            )
            await repo.save(report)
            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_subject(report_id)
            run = _authorize_report_workflow(run, report_id, organization_id)
            expected_version = run.state_version
            run.transition_to(WorkflowState.FINALIZATION_PENDING)
            run.transition_to(WorkflowState.PDF_PENDING)
            run.request_dispatch()
            await run_repo.save(run, expected_version=expected_version)
            self._uow.register(report)
            self._uow.register(run)
        return report


class RetryReportWorkflowHandler:
    """Re-run the parked stage of a report's workflow.

    Which stage to retry follows from the report's own status: a draft
    re-runs the AI analysis, a signed report retries PDF generation.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, *, report_id: UUID, organization_id: UUID) -> Report:
        async with self._uow:
            report = await ReportRepository(self._uow.session).get_by_id(report_id)
            if report is None or report.organization_id != organization_id:
                raise AuthorizationError(
                    f"Report {report_id} does not belong to organization {organization_id}."
                )
            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_subject(report_id)
            run = _authorize_report_workflow(run, report_id, organization_id)
            if run.state not in {
                WorkflowState.MANUAL_INPUT_REQUIRED,
                WorkflowState.FAILED,
            }:
                raise ReportStateError("This report's workflow has nothing to retry.")

            if report.status == "draft":
                target = WorkflowState.DRAFTING_PENDING
            elif report.status == "signed":
                target = WorkflowState.PDF_PENDING
            else:
                raise ReportStateError(
                    f"A {report.status} report cannot be retried automatically."
                )

            expected_version = run.state_version
            run.resume_to(target)
            run.request_dispatch()
            await run_repo.save(run, expected_version=expected_version)
            self._uow.register(run)
        return report


def _authorize_report_workflow(
    run: WorkflowRun | None, report_id: UUID, organization_id: UUID
) -> WorkflowRun:
    if (
        run is None
        or run.organization_id != organization_id
        or run.workflow_type != "report_fulfillment"
        or run.subject_id != report_id
    ):
        raise AuthorizationError(
            f"Workflow for report {report_id} does not belong to "
            f"organization {organization_id}."
        )
    return run


async def _load_mutate_save(uow, report_id, organization_id, mutation):
    async with uow:
        repo = ReportRepository(uow.session)
        report = await repo.get_by_id(report_id)
        if report is None or report.organization_id != organization_id:
            raise AuthorizationError(
                f"Report {report_id} does not belong to organization {organization_id}."
            )
        mutation(report)
        await repo.save(report)
        uow.register(report)
    return report
