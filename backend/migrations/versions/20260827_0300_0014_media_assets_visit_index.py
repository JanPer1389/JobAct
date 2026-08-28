"""operations: index media assets for visit evidence-readiness lookups

Revision ID: 0014
Revises: 0013
"""

from __future__ import annotations

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "ix_media_assets_visit_phase_status",
        "media_assets",
        ["visit_id", "phase", "status"],
        schema="operations",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_media_assets_visit_phase_status",
        table_name="media_assets",
        schema="operations",
    )
