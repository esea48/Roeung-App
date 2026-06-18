"""fix parent/child relationship direction (member_id and related_member_id were swapped)

Revision ID: d4e5f6a7
Revises: c3d4e5f6
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE family_relationships
        SET member_id = related_member_id,
            related_member_id = member_id
        WHERE relationship_type IN ('child', 'parent')
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE family_relationships
        SET member_id = related_member_id,
            related_member_id = member_id
        WHERE relationship_type IN ('child', 'parent')
    """)
