from __future__ import annotations

from time import monotonic
from uuid import UUID

from jobact.contexts.media.infrastructure.media_asset_repository import (
    MediaAssetRepository,
)
from jobact.contexts.visual_audits.infrastructure.visual_audit_repository import (
    VisualAuditRepository,
)
from jobact.shared.application.ports import AiConnector, Clock, ObjectStorage
from jobact.shared.application.uow import UnitOfWork
from jobact.workflows.visual_audit.agent import run_visual_audit


class RunVisualAuditActivity:
    def __init__(self, uow: UnitOfWork, storage: ObjectStorage, connector: AiConnector | None, clock: Clock) -> None:
        self._uow = uow
        self._storage = storage
        self._connector = connector
        self._clock = clock

    async def run(self, attempt_id: UUID) -> None:
        started = monotonic()
        async with self._uow:
            repo = VisualAuditRepository(self._uow.session)
            attempt = await repo.get_by_id(attempt_id)
            if attempt is None or attempt.status in {"succeeded", "failed"}:
                return
            if attempt.status == "pending":
                attempt.start(now=self._clock.now())
                await repo.save(attempt)

        try:
            if self._connector is None:
                raise RuntimeError("no_ai_connector")
            image_pairs: list[tuple[bytes, str, bytes, str]] = []
            async with self._uow:
                media_repo = MediaAssetRepository(self._uow.session)
                for pair in attempt.photo_pairs:
                    before = await media_repo.get_by_id(pair.before_asset_id)
                    after = await media_repo.get_by_id(pair.after_asset_id)
                    if before is None or after is None:
                        raise RuntimeError("audit_media_missing")
                    image_pairs.append((await self._storage.download(before.storage_key), before.content_type, await self._storage.download(after.storage_key), after.content_type))
            agent_result = await run_visual_audit(
                self._connector, work_description=attempt.work_description,
                provided_price_usd=attempt.provided_price_usd, image_pairs=image_pairs,
            )
            result = agent_result.result.model_dump(mode="json")
            async with self._uow:
                repo = VisualAuditRepository(self._uow.session)
                current = await repo.get_by_id(attempt_id)
                if current is None or current.status != "running":
                    return
                current.succeed(
                    result=result, model=agent_result.model, prompt_tokens=agent_result.prompt_tokens,
                    completion_tokens=agent_result.completion_tokens, cost_usd=agent_result.cost_usd,
                    latency_ms=int((monotonic() - started) * 1000), now=self._clock.now(),
                )
                await repo.save(current)
        except Exception:  # noqa: BLE001 - provider/storage details must not leak
            async with self._uow:
                repo = VisualAuditRepository(self._uow.session)
                current = await repo.get_by_id(attempt_id)
                if current is not None and current.status == "running":
                    current.fail(failure_code="visual_audit_processing_failed", latency_ms=int((monotonic() - started) * 1000), now=self._clock.now())
                    await repo.save(current)
