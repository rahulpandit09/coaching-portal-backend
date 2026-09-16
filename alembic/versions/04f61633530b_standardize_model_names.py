"""standardize_model_names

Revision ID: 04f61633530b
Revises: 3fa4f7cae637
Create Date: 2026-07-17 14:35:09.578698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04f61633530b'
down_revision: Union[str, Sequence[str], None] = '3fa4f7cae637'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Drop the empty `submenu` table that FastAPI auto-created if both submenu and submenus exist
    if 'submenu' in tables and 'submenus' in tables:
        op.drop_table('submenu')

    # 2. Rename the old tables to preserve your data
    if 'RolePermission' in tables and 'role_permission' not in tables:
        op.rename_table('RolePermission', 'role_permission')
    if 'RoleSubMenu' in tables and 'role_submenu' not in tables:
        op.rename_table('RoleSubMenu', 'role_submenu')
    if 'submenus' in tables and 'submenu' not in tables:
        op.rename_table('submenus', 'submenu')

    # 3. Rename the primary key column in the submenu table
    inspector = sa.inspect(bind)
    if 'submenu' in inspector.get_table_names():
        submenu_cols = [c['name'] for c in inspector.get_columns('submenu')]
        if 'submenu_id' in submenu_cols and 'id' not in submenu_cols:
            op.alter_column('submenu', 'submenu_id', new_column_name='id')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'submenu' in tables:
        submenu_cols = [c['name'] for c in inspector.get_columns('submenu')]
        if 'id' in submenu_cols and 'submenu_id' not in submenu_cols:
            op.alter_column('submenu', 'id', new_column_name='submenu_id')
        if 'submenus' not in tables:
            op.rename_table('submenu', 'submenus')

    if 'role_submenu' in tables and 'RoleSubMenu' not in tables:
        op.rename_table('role_submenu', 'RoleSubMenu')
    if 'role_permission' in tables and 'RolePermission' not in tables:
        op.rename_table('role_permission', 'RolePermission')
