"""`RunReportAnalysisActivity` -- the single AI orchestration step.

One workflow step, two AI calls, one unified result: the text draft
(work report, materials, a suggested price derived from the drafted
work-unit count) and the BEFORE/AFTER visual comparison land on the same
`ReportRevision` together, or neither does.

Failure behavior: each configured provider gets one complete unified-analysis
attempt. If all fail, the activity writes a deterministic template revision
(so the technician is never left with an empty draft) AND terminates the run
as FAILED with a safe error code, together, in one execution. PydanticAI's own
`Agent(..., retries=2)` already retries schema-validation failures; this
activity adds no outer retry loop.

Both AI calls are bounded by `Settings.ai_request_timeout_seconds`, so a
hung provider fails over or terminates the run rather than stalling indefinitely.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal
from time import monotonic
from uuid import UUID

from jobact.contexts.customers.infrastructure.customer_repository import (
    CustomerRepository,
)
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.reports.domain.pricing import (
    SUGGESTED_AMOUNT_CURRENCY,
    suggested_amount_cents,
)
from jobact.contexts.reports.domain.report import Material, Report
from jobact.contexts.reports.infrastructure.report_repository import ReportRepository
from jobact.contexts.visits.infrastructure.visit_repository import VisitRepository
from jobact.contexts.visual_audits.domain.visual_audit import (
    PhotoPair,
    VisualAuditAttempt,
)
from jobact.contexts.visual_audits.infrastructure.visual_audit_repository import (
    VisualAuditRepository,
)
from jobact.shared.application.fx import (
    LocalFxSnapshot,
    convert_usd_cents,
    provided_price_usd,
)
from jobact.shared.application.ports import (
    AiConnector,
    Clock,
    IdGenerator,
    ObjectStorage,
)
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.report_fulfillment.agent import (
    DraftedMaterial,
    DraftedReport,
    ReportAnalysisContext,
    draft_report,
)
from jobact.workflows.report_fulfillment.failures import (
    WorkflowFailure,
    classify_analysis_failures,
    provider_http_status,
)
from jobact.workflows.report_fulfillment.repository import (
    WorkflowConcurrencyError,
    WorkflowRunRepository,
)
from jobact.workflows.report_fulfillment.states import WorkflowState
from jobact.workflows.report_fulfillment.step_repository import WorkflowStepRepository
from jobact.workflows.visual_audit.agent import run_visual_audit

_TEMPLATE_WORK_COMPLETED = (
    "AI analysis was unavailable for this report. Please review the "
    "technician's raw notes and photos and fill in the work completed, "
    "materials, and amount manually before proceeding."
)

_STEP_NAME = "run_report_analysis"
_MAX_PHOTO_PAIRS = 6

# Maps a user's interface-language preference to the AI-prompt phrase that
# requests output in that language. Unknown/missing locales fall back to
# English rather than failing the drafting run over a language lookup.
_RESPONSE_LANGUAGE_BY_LOCALE = {"en-US": "English", "ru-RU": "Russian"}

logger = logging.getLogger(__name__)


class ReportAnalysisEvidenceError(RuntimeError):
    """Evidence went missing between report creation and worker pickup."""


class RunReportAnalysisActivity:
    def __init__(
        self,
        uow: UnitOfWork,
        connector: AiConnector | None,
        object_storage: ObjectStorage,
        clock: Clock,
        id_generator: IdGenerator,
        fx: LocalFxSnapshot,
        draft_report_fn=draft_report,
        run_visual_audit_fn=run_visual_audit,
        connectors: Sequence[AiConnector] | None = None,
    ) -> None:
        self._uow = uow
        self._connectors = (
            tuple(connectors)
            if connectors is not None
            else ((connector,) if connector is not None else ())
        )
        self._object_storage = object_storage
        self._clock = clock
        self._id_generator = id_generator
        self._fx = fx
        self._draft_report = draft_report_fn
        self._run_visual_audit = run_visual_audit_fn

    async def run(self, *, report_id: UUID, run_id: UUID) -> None:
        started_at = self._clock.now()
        start_time = monotonic()

        loaded = await self._load_analysis_inputs(report_id, run_id)
        if loaded is None:
            return
        context, correlation_id, image_pairs, pair_asset_ids, revision_id = loaded

        logger.info(
            "report_workflow_started report_id=%s run_id=%s notes_chars=%s "
            "photo_pair_count=%s provider_count=%s correlation_id=%s",
            report_id,
            run_id,
            len(context.raw_notes),
            len(image_pairs),
            len(self._connectors),
            correlation_id,
        )

        drafted, audit_result, failure, model_used = await self._run_ai_steps(
            report_id=report_id,
            run_id=run_id,
            correlation_id=correlation_id,
            context=context,
            image_pairs=image_pairs,
        )
        latency_ms = int((monotonic() - start_time) * 1000)

        await self._persist_outcome(
            report_id=report_id,
            run_id=run_id,
            revision_id=revision_id,
            correlation_id=correlation_id,
            drafted=drafted,
            audit_result=audit_result,
            pair_asset_ids=pair_asset_ids,
            failure=failure,
            model_used=model_used,
            started_at=started_at,
            latency_ms=latency_ms,
        )

    async def _load_analysis_inputs(self, report_id: UUID, run_id: UUID):
        """Load everything the AI steps need, or `None` if this run is not
        actually awaiting analysis (duplicate/stale event delivery).
        """
        async with self._uow:
            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_id(run_id)
            if (
                run is None
                or run.subject_id != report_id
                or run.state != WorkflowState.DRAFTING_PENDING
                or run.claimed_at is not None
            ):
                return None

            # Atomically claim exclusive execution before paying for the AI
            # calls below. `claimed_at` (not just `state`) is the marker: the
            # run doesn't leave DRAFTING_PENDING until the AI calls finish,
            # so a second, later dispatch of the SAME pending step would
            # otherwise see the identical state and re-run them. The
            # compare-and-swap save() additionally protects the narrower
            # window where two dispatches load the run at the same instant,
            # before either's claim has committed.
            claimed_version = run.state_version
            run.claim_attempt(now=self._clock.now())
            try:
                await run_repo.save(run, expected_version=claimed_version)
            except WorkflowConcurrencyError:
                logger.info(
                    "report_analysis_claim_lost report_id=%s run_id=%s",
                    report_id,
                    run_id,
                )
                return None

            report = await ReportRepository(self._uow.session).get_by_id(report_id)
            if report is None:
                return None

            drafting_input = run.input_data.get("drafting")
            raw_notes = (
                drafting_input.get("raw_notes")
                if isinstance(drafting_input, dict)
                else None
            )
            if not isinstance(raw_notes, str):
                raise TypeError(f"Workflow run {run_id} has no drafting raw_notes.")

            visit = await VisitRepository(self._uow.session).get_by_id(report.visit_id)
            if visit is None:
                raise ValueError(f"Visit {report.visit_id} does not exist.")
            customer = await CustomerRepository(self._uow.session).get_by_id(
                visit.customer_id
            )
            if customer is None:
                raise ValueError(f"Customer {visit.customer_id} does not exist.")

            media_repo = MediaAssetRepository(self._uow.session)
            before = await media_repo.list_attached_by_visit_and_phase(
                visit.id, "before"
            )
            after = await media_repo.list_attached_by_visit_and_phase(visit.id, "after")

            revision = report.current_revision
            creator = (
                await UserRepository(self._uow.session).get_by_id(revision.created_by)
                if revision.created_by is not None
                else None
            )
            response_language = _RESPONSE_LANGUAGE_BY_LOCALE.get(
                creator.locale if creator is not None else "", "English"
            )
            context = ReportAnalysisContext(
                raw_notes=raw_notes,
                customer_name=customer.name,
                customer_address=customer.address,
                customer_service_type=customer.service_type,
                gps_lat=visit.gps_lat,
                gps_lon=visit.gps_lon,
                current_work_completed=revision.work_completed or None,
                current_materials=[
                    DraftedMaterial(label=m.label, qty=m.qty)
                    for m in revision.materials
                ],
                current_amount_cents=revision.amount_cents,
                currency=revision.currency,
                response_language=response_language,
            )

            # Readiness was enforced at report creation; assets can still
            # go missing before the worker picks the job up. Surface that
            # as an analysis failure, never as an unhandled crash.
            image_pairs: list[tuple[bytes, str, bytes, str]] = []
            pair_asset_ids: list[PhotoPair] = []
            if before and len(before) == len(after):
                for before_asset, after_asset in zip(
                    before[:_MAX_PHOTO_PAIRS], after[:_MAX_PHOTO_PAIRS], strict=True
                ):
                    image_pairs.append(
                        (
                            await self._object_storage.download(
                                before_asset.storage_key
                            ),
                            before_asset.content_type,
                            await self._object_storage.download(
                                after_asset.storage_key
                            ),
                            after_asset.content_type,
                        )
                    )
                    pair_asset_ids.append(
                        PhotoPair(
                            before_asset_id=before_asset.id,
                            after_asset_id=after_asset.id,
                        )
                    )

            return (
                context,
                run.correlation_id,
                image_pairs,
                pair_asset_ids,
                revision.id,
            )

    async def _run_ai_steps(
        self, *, report_id, run_id, correlation_id, context, image_pairs
    ):
        """Draft the report, then compare its photos. Either both succeed
        or the whole step is treated as failed -- one atomic outcome.
        """
        errors: list[Exception] = []
        for connector in self._connectors:
            result = await self._try_provider(
                connector=connector,
                report_id=report_id,
                run_id=run_id,
                correlation_id=correlation_id,
                context=context,
                image_pairs=image_pairs,
            )
            if isinstance(result, Exception):
                errors.append(result)
                continue
            return result

        failure = classify_analysis_failures(errors)
        return _template_fallback(), None, failure, None

    async def _try_provider(
        self, *, connector, report_id, run_id, correlation_id, context, image_pairs
    ):
        """Run the complete unified analysis on one provider."""
        try:
            logger.info(
                "report_ai_request_started report_id=%s run_id=%s step=drafting "
                "provider=%s notes_chars=%s correlation_id=%s",
                report_id,
                run_id,
                connector.provider_name,
                len(context.raw_notes),
                correlation_id,
            )
            drafting_started = monotonic()
            drafting_result = await self._draft_report(connector, context)
            logger.info(
                "report_ai_request_succeeded report_id=%s run_id=%s step=drafting "
                "model=%s latency_ms=%s correlation_id=%s",
                report_id,
                run_id,
                drafting_result.model,
                int((monotonic() - drafting_started) * 1000),
                correlation_id,
            )
        except Exception as exc:  # noqa: BLE001 -- any failure falls back to
            # the template draft; provider details must not propagate.
            logger.warning(
                "report_ai_request_failed report_id=%s run_id=%s step=drafting "
                "error_type=%s provider_http_status=%s correlation_id=%s",
                report_id,
                run_id,
                type(exc).__name__,
                provider_http_status(exc),
                correlation_id,
            )
            return exc

        drafted = drafting_result.draft
        try:
            if not image_pairs:
                raise ReportAnalysisEvidenceError(
                    "No comparable before/after photo pairs are attached."
                )
            logger.info(
                "report_ai_request_started report_id=%s run_id=%s "
                "step=visual_comparison provider=%s photo_pair_count=%s "
                "work_description_chars=%s correlation_id=%s",
                report_id,
                run_id,
                connector.provider_name,
                len(image_pairs),
                len(drafted.work_completed),
                correlation_id,
            )
            audit_started = monotonic()
            agent_result = await self._run_visual_audit(
                connector,
                work_description=drafted.work_completed,
                provided_price_usd=provided_price_usd(
                    suggested_amount_cents(drafted.estimated_work_units),
                    SUGGESTED_AMOUNT_CURRENCY,
                    self._fx.usd_rub_rate,
                ),
                image_pairs=image_pairs,
                customer_service_type=context.customer_service_type,
                gps_lat=context.gps_lat,
                gps_lon=context.gps_lon,
                response_language=context.response_language,
            )
            logger.info(
                "report_ai_request_succeeded report_id=%s run_id=%s "
                "step=visual_comparison model=%s latency_ms=%s correlation_id=%s",
                report_id,
                run_id,
                agent_result.model,
                int((monotonic() - audit_started) * 1000),
                correlation_id,
            )
        except Exception as exc:  # noqa: BLE001 -- see above; a failed
            # comparison invalidates the whole unified result.
            logger.warning(
                "report_ai_request_failed report_id=%s run_id=%s "
                "step=visual_comparison error_type=%s provider_http_status=%s "
                "correlation_id=%s",
                report_id,
                run_id,
                type(exc).__name__,
                provider_http_status(exc),
                correlation_id,
            )
            return exc

        return drafted, agent_result, None, drafting_result.model

    async def _persist_outcome(
        self,
        *,
        report_id,
        run_id,
        revision_id,
        correlation_id,
        drafted,
        audit_result,
        pair_asset_ids,
        failure: WorkflowFailure | None,
        model_used,
        started_at,
        latency_ms,
    ) -> None:
        now = self._clock.now()
        async with self._uow:
            report_repo = ReportRepository(self._uow.session)
            report = await report_repo.get_by_id(report_id)
            if report is None:
                raise ValueError(f"Report {report_id} does not exist.")

            comparison: dict | None = (
                audit_result.result.model_dump(mode="json")
                if audit_result is not None
                else None
            )
            revision_currency = report.current_revision.currency
            converted_amount_cents = _apply_result(
                report,
                drafted,
                self._id_generator,
                currency=revision_currency,
                usd_rub_rate=self._fx.usd_rub_rate,
                visual_comparison_status=(
                    "succeeded" if audit_result is not None else None
                ),
                visual_comparison=comparison,
            )
            await report_repo.save(report)
            self._uow.register(report)

            if audit_result is not None and comparison is not None:
                attempt = VisualAuditAttempt.request(
                    id=self._id_generator.new_id(),
                    organization_id=report.organization_id,
                    report_id=report.id,
                    report_revision_id=revision_id,
                    visit_id=report.visit_id,
                    photo_pairs=list(pair_asset_ids),
                    work_description=drafted.work_completed,
                    amount_cents=converted_amount_cents,
                    currency=revision_currency,
                    provided_price_usd=provided_price_usd(
                        converted_amount_cents,
                        revision_currency,
                        self._fx.usd_rub_rate,
                    ),
                    usd_rub_rate=self._fx.usd_rub_rate,
                    usd_rub_rate_date=self._fx.effective_date,
                    usd_rub_rate_source=self._fx.source,
                    created_at=now,
                )
                attempt.start(now=now)
                attempt.succeed(
                    result=comparison,
                    model=audit_result.model,
                    prompt_tokens=audit_result.prompt_tokens,
                    completion_tokens=audit_result.completion_tokens,
                    cost_usd=audit_result.cost_usd,
                    latency_ms=latency_ms,
                    now=now,
                )
                # Drain the request event: the comparison already ran here,
                # so nothing should consume it from the outbox.
                attempt.pull_events()
                await VisualAuditRepository(self._uow.session).add(attempt)

            run_repo = WorkflowRunRepository(self._uow.session)
            run = await run_repo.get_by_id(run_id)
            if run is None:
                raise ValueError(f"Workflow run {run_id} does not exist.")
            expected_version = run.state_version

            if failure is None:
                run.record_step_success()
                run.transition_to(WorkflowState.REVIEW_PENDING)
                step_status = "succeeded"
                output_data = {"model": model_used, "latency_ms": latency_ms}
            else:
                run.fail(code=failure.code, now=started_at)
                step_status = "failed"
                output_data = {
                    "model": None,
                    "latency_ms": latency_ms,
                    "error_code": failure.code,
                    "http_status": failure.http_status,
                    "retryable": failure.retryable,
                }

            await run_repo.save(run, expected_version=expected_version)
            await WorkflowStepRepository(self._uow.session).record(
                id=self._id_generator.new_id(),
                run_id=run.id,
                step=_STEP_NAME,
                status=step_status,
                attempt=run.attempt,
                input_data=None,
                output_data=output_data,
                error=failure.code if failure is not None else None,
                started_at=started_at,
                finished_at=now,
            )
            self._uow.register(run)

        if failure is None:
            logger.info(
                "report_analysis_persisted report_id=%s run_id=%s state=%s "
                "latency_ms=%s correlation_id=%s",
                report_id,
                run_id,
                WorkflowState.REVIEW_PENDING.value,
                latency_ms,
                correlation_id,
            )
        else:
            logger.warning(
                "report_workflow_failed report_id=%s run_id=%s "
                "error_code=%s http_status=%s latency_ms=%s correlation_id=%s",
                report_id,
                run_id,
                failure.code,
                failure.http_status,
                latency_ms,
                correlation_id,
            )


def _apply_result(
    report: Report,
    drafted: DraftedReport,
    id_generator: IdGenerator,
    *,
    currency: str,
    usd_rub_rate: Decimal,
    visual_comparison_status: str | None,
    visual_comparison: dict | None,
) -> int | None:
    """Apply the drafted result to `report`, converting the deterministic
    USD base amount into `currency` (the revision's snapshotted currency,
    never touched here -- see `Report.apply_ai_unified_result`). Returns
    the converted amount so the caller can reuse it for the
    `VisualAuditAttempt` record without recomputing.
    """
    base_usd_cents = suggested_amount_cents(drafted.estimated_work_units)
    converted_amount_cents = convert_usd_cents(base_usd_cents, currency, usd_rub_rate)
    report.apply_ai_unified_result(
        work_completed=drafted.work_completed,
        materials=[
            Material(id=id_generator.new_id(), label=material.label, qty=material.qty)
            for material in drafted.materials
        ],
        amount_cents=converted_amount_cents,
        ai_confidence=drafted.confidence,
        visual_comparison_status=visual_comparison_status,
        visual_comparison=visual_comparison,
    )
    return converted_amount_cents


def _template_fallback() -> DraftedReport:
    return DraftedReport(
        work_completed=_TEMPLATE_WORK_COMPLETED,
        materials=[],
        estimated_work_units=None,
        confidence="low",
    )
