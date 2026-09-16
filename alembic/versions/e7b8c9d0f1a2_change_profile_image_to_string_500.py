"""change_profile_image_to_string_500

Revision ID: e7b8c9d0f1a2
Revises: 23a470ce9123
Create Date: 2026-08-31 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b8c9d0f1a2'
down_revision: Union[str, Sequence[str], None] = '23a470ce9123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'users' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'profile_image' in user_cols:
            # Clear legacy Base64 string data or values exceeding 500 chars before altering column
            op.execute("UPDATE users SET profile_image = NULL WHERE profile_image LIKE 'data:image%' OR length(profile_image) > 500")
            op.alter_column(
                'users',
                'profile_image',
                type_=sa.String(length=500),
                existing_type=sa.Text(),
                existing_nullable=True
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'users' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'profile_image' in user_cols:
            op.alter_column(
                'users',
                'profile_image',
                type_=sa.Text(),
                existing_type=sa.String(length=500),
                existing_nullable=True
            )
