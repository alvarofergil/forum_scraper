"""Harden HITO-01 persistence contracts.

Revision ID: 0002_hito_01_corrective_hardening
Revises: 0001_initial_schema
Create Date: 2026-09-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_hito_01_corrective_hardening"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "favorites",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("favorites", sa.Column("last_checked_at", sa.DateTime(timezone=True)))
    op.add_column("favorites", sa.Column("last_content_hash", sa.String(length=128)))
    op.add_column("favorites", sa.Column("last_classified_at", sa.DateTime(timezone=True)))
    op.add_column("events", sa.Column("payload_json", sa.Text()))


def downgrade() -> None:
    op.drop_column("events", "payload_json")
    op.drop_column("favorites", "last_classified_at")
    op.drop_column("favorites", "last_content_hash")
    op.drop_column("favorites", "last_checked_at")
    op.drop_column("favorites", "is_active")
