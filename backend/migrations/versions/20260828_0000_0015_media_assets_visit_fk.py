"""operations: enforce media asset visit references

Revision ID: 0015
Revises: 0014
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | None = None
depends_on: str | None = None

_CONSTRAINT_NAME = "fk_media_assets_visit_id_visits"
_PREFLIGHT_REPORT = "docs/operations/media_assets_visit_fk_preflight.sql"


def upgrade() -> None:
    orphan_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM operations.media_assets AS media_asset
            LEFT JOIN operations.visits AS visit
              ON visit.id = media_asset.visit_id
            WHERE media_asset.visit_id IS NOT NULL
              AND visit.id IS NULL
            """
        )
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            "Cannot add media-assets visit foreign key: "
            f"found {orphan_count} orphaned row(s). "
            f"Run {_PREFLIGHT_REPORT}, review and repair the data, then retry."
        )

    op.create_foreign_key(
        _CONSTRAINT_NAME,
        "media_assets",
        "visits",
        ["visit_id"],
        ["id"],
        source_schema="operations",
        referent_schema="operations",
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    op.drop_constraint(
        _CONSTRAINT_NAME,
        "media_assets",
        schema="operations",
        type_="foreignkey",
    )
