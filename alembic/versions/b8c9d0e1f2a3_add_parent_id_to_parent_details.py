"""add parent_id to parent_details table

Revision ID: b8c9d0e1f2a3
Revises: 92f1c9858ecb
Create Date: 2026-10-01 12:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = '855b9813ed70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'parent_details' in tables:
        parent_cols = [c['name'] for c in inspector.get_columns('parent_details')]
        if 'parent_id' not in parent_cols:
            op.add_column('parent_details', sa.Column('parent_id', sa.String(length=100), nullable=True))

        parent_idx = [idx['name'] for idx in inspector.get_indexes('parent_details')]
        if 'ix_parent_details_parent_id' not in parent_idx:
            op.create_index(op.f('ix_parent_details_parent_id'), 'parent_details', ['parent_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'parent_details' in tables:
        parent_idx = [idx['name'] for idx in inspector.get_indexes('parent_details')]
        if 'ix_parent_details_parent_id' in parent_idx:
            op.drop_index(op.f('ix_parent_details_parent_id'), table_name='parent_details')

        parent_cols = [c['name'] for c in inspector.get_columns('parent_details')]
        if 'parent_id' in parent_cols:
            op.drop_column('parent_details', 'parent_id')
