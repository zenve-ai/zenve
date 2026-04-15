"""add redis_username and redis_password_hash to organizations

Revision ID: 0001
Revises:
Create Date: 2026-04-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("redis_username", sa.String(128), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("redis_password_hash", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "redis_password_hash")
    op.drop_column("organizations", "redis_username")
