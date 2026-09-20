"""add video source metadata

Revision ID: 0002_add_video_source_metadata
Revises: 0001_create_video_sources
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_video_source_metadata"
down_revision = "0001_create_video_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_sources",
        sa.Column("enabled", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "video_sources",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "video_sources",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE video_sources
            SET enabled = 1,
                created_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE enabled IS NULL OR created_at IS NULL OR updated_at IS NULL
            """
        )
    )

    with op.batch_alter_table("video_sources") as batch_op:
        batch_op.alter_column(
            "enabled",
            nullable=False,
            server_default=sa.true(),
        )
        batch_op.alter_column(
            "created_at",
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.alter_column(
            "updated_at",
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )


def downgrade() -> None:
    with op.batch_alter_table("video_sources") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("enabled")
