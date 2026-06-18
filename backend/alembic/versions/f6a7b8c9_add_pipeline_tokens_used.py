"""Add pipeline_tokens_used to stories

Revision ID: f6a7b8c9
Revises: e5f6a7b8
Create Date: 2026-06-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stories', sa.Column('pipeline_tokens_used', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('stories', 'pipeline_tokens_used')
