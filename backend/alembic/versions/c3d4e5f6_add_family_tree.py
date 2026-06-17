"""add family tree (family_relationships table + gender + is_tree_member on family_members)

Revision ID: c3d4e5f6
Revises: b1c2d3e4f5a6
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE gender AS ENUM ('male', 'female', 'other', 'unknown')")
    op.execute("ALTER TABLE family_members ADD COLUMN gender gender")
    op.execute("ALTER TABLE family_members ADD COLUMN is_tree_member BOOLEAN NOT NULL DEFAULT FALSE")

    op.execute("CREATE TYPE relationship_type AS ENUM ('parent', 'child', 'spouse', 'sibling')")
    op.execute("""
        CREATE TABLE family_relationships (
            id          UUID        PRIMARY KEY,
            family_id   UUID        NOT NULL REFERENCES families(id),
            member_id   UUID        NOT NULL REFERENCES family_members(id),
            related_member_id UUID  NOT NULL REFERENCES family_members(id),
            relationship_type relationship_type NOT NULL,
            created_by  UUID        REFERENCES keepers(id),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_family_relationships_family_id ON family_relationships (family_id)")
    op.execute("CREATE INDEX ix_family_relationships_member_id ON family_relationships (member_id)")
    op.execute("CREATE INDEX ix_family_relationships_related_member_id ON family_relationships (related_member_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_family_relationships_related_member_id")
    op.execute("DROP INDEX IF EXISTS ix_family_relationships_member_id")
    op.execute("DROP INDEX IF EXISTS ix_family_relationships_family_id")
    op.execute("DROP TABLE IF EXISTS family_relationships")
    op.execute("ALTER TABLE family_members DROP COLUMN IF EXISTS is_tree_member")
    op.execute("ALTER TABLE family_members DROP COLUMN IF EXISTS gender")
    op.execute("DROP TYPE IF EXISTS relationship_type")
    op.execute("DROP TYPE IF EXISTS gender")
