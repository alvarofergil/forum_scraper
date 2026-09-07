"""Create initial Forum Scraper schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

availability_status = ("AVAILABLE", "RESERVED", "SOLD", "WITHDRAWN", "UNKNOWN")
candidate_status = ("PENDING", "CLASSIFIED", "DISCARDED")
event_type = (
    "NEW_FAVORITE",
    "PRICE_CHANGED",
    "STATUS_CHANGED",
    "BECAME_UNAVAILABLE",
    "FAVORITE_REACTIVATED",
    "ERROR",
)
notification_status = ("PENDING", "SENT", "FAILED")


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_topic_id", sa.String(length=64), nullable=False),
        sa.Column("canonical_url", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("snippet", sa.String(length=1000), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_post_author", sa.String(length=255), nullable=True),
        sa.Column("reply_count", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_topic_id", name="uq_topics_external_topic_id"),
    )
    op.create_index("ix_topics_last_activity_at", "topics", ["last_activity_at"])

    op.create_table(
        "candidate_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("watch_item_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"status IN {candidate_status}",
            name="ck_candidate_matches_status",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("topic_id", "watch_item_id", name="uq_candidate_topic_watch_item"),
    )

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("watch_item_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("price_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unavailable_confirmation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"status IN {availability_status}",
            name="ck_favorites_status",
        ),
        sa.CheckConstraint(
            "unavailable_confirmation_count >= 0",
            name="ck_favorites_unavailable_confirmation_count",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("topic_id", name="uq_favorites_topic_id"),
    )
    op.create_index("ix_favorites_watch_item_id", "favorites", ["watch_item_id"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("favorite_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["favorite_id"], ["favorites.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_price_history_favorite_id", "price_history", ["favorite_id"])

    op.create_table(
        "status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("favorite_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"status IN {availability_status}",
            name="ck_status_history_status",
        ),
        sa.ForeignKeyConstraint(["favorite_id"], ["favorites.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_status_history_favorite_id", "status_history", ["favorite_id"])

    op.create_table(
        "topic_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("external_post_id", sa.String(length=64), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("topic_id", "sequence_number", name="uq_topic_posts_sequence"),
    )
    op.create_index("ix_topic_posts_topic_id", "topic_posts", ["topic_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("favorite_id", sa.Integer(), nullable=True),
        sa.Column("watch_item_id", sa.String(length=255), nullable=True),
        sa.Column("notification_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(f"event_type IN {event_type}", name="ck_events_event_type"),
        sa.CheckConstraint(
            f"notification_status IN {notification_status}",
            name="ck_events_notification_status",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["favorite_id"], ["favorites.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("deduplication_key", name="uq_events_deduplication_key"),
    )
    op.create_index("ix_events_created_at", "events", ["created_at"])

    op.create_table(
        "app_state",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.String(length=1000), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_state")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_topic_posts_topic_id", table_name="topic_posts")
    op.drop_table("topic_posts")
    op.drop_index("ix_status_history_favorite_id", table_name="status_history")
    op.drop_table("status_history")
    op.drop_index("ix_price_history_favorite_id", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("ix_favorites_watch_item_id", table_name="favorites")
    op.drop_table("favorites")
    op.drop_table("candidate_matches")
    op.drop_index("ix_topics_last_activity_at", table_name="topics")
    op.drop_table("topics")
