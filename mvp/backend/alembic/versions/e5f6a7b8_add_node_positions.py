"""Add position_col and position_row to family_members for snap-to-grid node placement

Revision ID: e5f6a7b8
Revises: d4e5f6a7
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('family_members', sa.Column('position_col', sa.Integer(), nullable=True))
    op.add_column('family_members', sa.Column('position_row', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('family_members', 'position_row')
    op.drop_column('family_members', 'position_col')
