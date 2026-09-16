"""add phone_number to users table

Revision ID: e7a1b6d04a30
Revises: e7b8c9d0f1a2
Create Date: 2026-09-04 11:37:46.824107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a1b6d04a30'
down_revision: Union[str, Sequence[str], None] = 'e7b8c9d0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'users' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'phone_number' not in user_cols:
            op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'users' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'phone_number' in user_cols:
            op.drop_column('users', 'phone_number')
