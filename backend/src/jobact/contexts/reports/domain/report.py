"""The report aggregate and its forward-only signing state machine.

Revisions, materials, and signatures belong to one report lifecycle. They
therefore live as nested data under ``Report`` rather than as independently
loadable aggregate roots, even though persistence normalizes them into their
own tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from jobact.shared.domain.aggregate import AggregateRoot


class ReportStateError(Exception):
    """Raised when a report transition would violate a domain invariant."""


@dataclass(frozen=True)
class Material:
    id: UUID
    label: str
    qty: str


@dataclass
class ReportRevision:
    id: UUID
    revision_no: int
    source: str
    work_completed: str
    amount_cents: int | None
    currency: str
    ai_confidence: str | None
    created_at: datetime
    created_by: UUID | None
    confirmed_by_user_at: datetime | None = None
    amount_confirmed_at: datetime | None = None
    frozen_at: datetime | None = None
    materials: list[Material] = field(default_factory=list)
    visual_comparison_status: str | None = None
    visual_comparison: dict[str, Any] | None = None


@dataclass(frozen=True)
class Signature:
    id: UUID
    signer_name: str
    signed_at: datetime
    media_asset_id: UUID
    ip: str | None
    user_agent: str | None


class Report(AggregateRoot):
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        visit_id: UUID,
        human_id: str,
        status: str,
        current_revision: ReportRevision,
        signed_at: datetime | None = None,
        completed_at: datetime | None = None,
        signatures: list[Signature] | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.organization_id = organization_id
        self.visit_id = visit_id
        self.human_id = human_id
        self.status = status
        self.current_revision = current_revision
        self.signed_at = signed_at
        self.completed_at = completed_at
        self.signatures = list(signatures) if signatures else []

    @classmethod
    def create_draft(
        cls,
        *,
        id: UUID,
        organization_id: UUID,
        visit_id: UUID,
        human_id: str,
        revision_id: UUID,
        created_at: datetime,
        created_by: UUID | None,
        currency: str,
    ) -> Report:
        return cls(
            id=id,
            organization_id=organization_id,
            visit_id=visit_id,
            human_id=human_id,
            status="draft",
            current_revision=ReportRevision(
                id=revision_id,
                revision_no=1,
                source="human",
                work_completed="",
                amount_cents=None,
                currency=currency,
                ai_confidence=None,
                created_at=created_at,
                created_by=created_by,
            ),
        )

    def apply_ai_unified_result(
        self,
        *,
        work_completed: str,
        materials: list[Material],
        amount_cents: int | None,
        ai_confidence: str,
        visual_comparison_status: str | None = None,
        visual_comparison: dict[str, Any] | None = None,
    ) -> None:
        """Apply one unified analysis result: the drafted work report plus
        the BEFORE/AFTER visual comparison produced in the same run.

        The amount is advisory only: this method never sets
        `confirmed_by_user_at`/`amount_confirmed_at`, so
        `mark_ready_for_signature()` still requires an explicit human
        confirmation regardless of `ai_confidence` or the suggested amount.

        Deliberately does not take a `currency` -- the revision's currency
        is a snapshot of the creating user's preference at report-creation
        time (see `create_draft`), and stays fixed for the life of the
        report. `amount_cents` is expected to already be denominated in
        `revision.currency` (the caller converts the deterministic USD
        base amount before calling this).
        """
        self._ensure_editable()
        revision = self.current_revision
        revision.source = "ai"
        revision.work_completed = work_completed
        revision.materials = list(materials)
        revision.amount_cents = amount_cents
        revision.ai_confidence = ai_confidence
        revision.visual_comparison_status = visual_comparison_status
        revision.visual_comparison = visual_comparison

    def update_revision(
        self,
        *,
        work_completed: str,
        amount_cents: int | None,
        currency: str | None = None,
        materials: list[Material] | None = None,
    ) -> None:
        self._ensure_editable()
        revision = self.current_revision
        revision.source = "human"
        revision.work_completed = work_completed
        revision.amount_cents = amount_cents
        if currency is not None:
            revision.currency = currency
        if materials is not None:
            revision.materials = list(materials)
        revision.confirmed_by_user_at = None
        revision.amount_confirmed_at = None

    def confirm(self, *, now: datetime) -> None:
        self._ensure_editable()
        self.current_revision.confirmed_by_user_at = now
        self.current_revision.amount_confirmed_at = now

    def freeze_revision(self, *, now: datetime) -> None:
        self._ensure_editable()
        if self.current_revision.frozen_at is not None:
            raise ReportStateError("The current report revision is already frozen.")
        self.current_revision.frozen_at = now

    def mark_ready_for_signature(self, *, now: datetime) -> None:
        self._ensure_editable()
        revision = self.current_revision
        if (
            revision.confirmed_by_user_at is None
            or revision.amount_confirmed_at is None
        ):
            raise ReportStateError(
                "A report must be confirmed before it can be signed."
            )
        self.freeze_revision(now=now)
        self.status = "pending_signature"

    def sign(
        self,
        *,
        signer_name: str,
        signature_media_asset_id: UUID | None,
        ip: str | None,
        user_agent: str | None,
        now: datetime,
        signature_id: UUID | None = None,
    ) -> None:
        if self.status != "pending_signature":
            raise ReportStateError("Only a report pending signature can be signed.")
        if self.current_revision.frozen_at is None:
            raise ReportStateError("A report revision must be frozen before signing.")
        if signature_media_asset_id is None:
            raise ReportStateError("An attached signature asset is required to sign.")
        self.signatures.append(
            Signature(
                id=signature_id or signature_media_asset_id,
                signer_name=signer_name,
                signed_at=now,
                media_asset_id=signature_media_asset_id,
                ip=ip,
                user_agent=user_agent,
            )
        )
        self.status = "signed"
        self.signed_at = now

    def complete(self, *, now: datetime) -> None:
        if self.status != "signed":
            raise ReportStateError("Only a signed report can be completed.")
        self.status = "completed"
        self.completed_at = now

    def _ensure_editable(self) -> None:
        if self.status != "draft":
            raise ReportStateError("Only draft reports can be edited.")
        if self.current_revision.frozen_at is not None:
            raise ReportStateError("A frozen report revision cannot be edited.")
