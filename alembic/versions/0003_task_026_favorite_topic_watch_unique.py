"""Allow one favorite per topic and watch item.

Revision ID: 0003_task_026_favorite_topic_watch_unique
Revises: 0002_hito_01_corrective_hardening
Create Date: 2026-09-09
"""

from __future__ import annotations

from alembic import op

revision = "0003_task_026_favorite_topic_watch_unique"
down_revision = "0002_hito_01_corrective_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("favorites") as batch:
        batch.drop_constraint("uq_favorites_topic_id", type_="unique")
        batch.create_unique_constraint(
            "uq_favorites_topic_watch_item",
            ["topic_id", "watch_item_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("favorites") as batch:
        batch.drop_constraint("uq_favorites_topic_watch_item", type_="unique")
        batch.create_unique_constraint("uq_favorites_topic_id", ["topic_id"])
