"""add audio_language and story-level edited text fields

Revision ID: b1c2d3e4f5a6
Revises: a400556d2783
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a400556d2783'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'stories',
        sa.Column(
            'audio_language',
            sa.Enum('en', 'kh', name='language', create_type=False),
            nullable=True,
        ),
    )
    op.add_column('stories', sa.Column('transcript_edited', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('translation_edited', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('stories', 'translation_edited')
    op.drop_column('stories', 'transcript_edited')
    op.drop_column('stories', 'audio_language')
