"""Report command/query handlers -- thin orchestration over
`UnitOfWork` + `ReportRepository`, same pattern as every other context.

`raw_notes` (the create-report input) is NOT read from
`visits.raw_notes` -- per this plan's own ruling, `POST /reports`'s
request body is the sole authoritative source for AI drafting input.
This task only persists `raw_notes` implicitly via the eventual AI
drafting workflow (Task 4.3/4.4); it is not stored on the Report/
ReportRevision itself in this task's scope -- the workflow that
consumes it hasn't been built yet.
"""

from __future__ import annotations

from uuid import UUID

from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.domain.report import Material, Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.shared.application.authorization import AuthorizationError
from jobact.shared.application.ports import Clock, IdGenerator
from jobact.shared.application.uow import UnitOfWork


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
    ) -> Report:
        async with self._uow:
            visit = await VisitRepository(self._uow.session).get_by_id(visit_id)
            if visit is None or visit.organization_id != organization_id:
                raise AuthorizationError(
                    f"Visit {visit_id} does not belong to organization {organization_id}."
                )

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
            self._uow.register(report)
        return report


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
        return await _load_mutate_save(
            self._uow,
            report_id,
            organization_id,
            lambda report: report.mark_ready_for_signature(now=self._clock.now()),
        )


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
            self._uow.register(report)
        return report


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
