"""create video sources table

Revision ID: 0001_create_video_sources
Revises:
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_create_video_sources"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "devices" in table_names and "video_sources" not in table_names:
        op.rename_table("devices", "video_sources")
        table_names = [*table_names, "video_sources"]

    if "video_sources" not in table_names:
        op.create_table(
            "video_sources",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("stream_id", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("stream_id"),
        )
        op.create_index("ix_video_sources_id", "video_sources", ["id"], unique=False)
        op.create_index("ix_video_sources_stream_id", "video_sources", ["stream_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "video_sources" not in inspector.get_table_names():
        return
    op.drop_index("ix_video_sources_stream_id", table_name="video_sources")
    op.drop_index("ix_video_sources_id", table_name="video_sources")
    op.drop_table("video_sources")
