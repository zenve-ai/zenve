"""drop_agents_table

Revision ID: b3e9f2d1a4c7
Revises: ccf0a808e05e
Create Date: 2026-04-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3e9f2d1a4c7"
down_revision: str | None = "ccf0a808e05e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("agents")


def downgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("dir_path", sa.String(), nullable=False),
        sa.Column("adapter_type", sa.String(), nullable=False),
        sa.Column("adapter_config", sa.JSON(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("tools", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("heartbeat_interval_seconds", sa.Integer(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("org_id", "name"),
        sa.UniqueConstraint("org_id", "slug"),
    )
