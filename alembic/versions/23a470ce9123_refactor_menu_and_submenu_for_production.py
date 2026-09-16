"""Refactor Menu and SubMenu for production

Revision ID: 23a470ce9123
Revises: 04f61633530b
Create Date: 2026-07-17 16:25:46.974512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23a470ce9123'
down_revision: Union[str, Sequence[str], None] = '04f61633530b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'menu' in tables:
        menu_cols = [c['name'] for c in inspector.get_columns('menu')]
        if 'order_index' not in menu_cols:
            op.add_column('menu', sa.Column('order_index', sa.Integer(), nullable=True))
        if 'is_deleted' not in menu_cols:
            op.add_column('menu', sa.Column('is_deleted', sa.Boolean(), nullable=True))
        if 'created_at' not in menu_cols:
            op.add_column('menu', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
        if 'updated_at' not in menu_cols:
            op.add_column('menu', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

        menu_indexes = [idx['name'] for idx in inspector.get_indexes('menu')]
        if 'ix_menu_order_index' not in menu_indexes:
            op.create_index(op.f('ix_menu_order_index'), 'menu', ['order_index'], unique=False)

        try:
            op.create_unique_constraint(None, 'menu', ['title'])
        except Exception:
            pass
        try:
            op.create_unique_constraint(None, 'menu', ['path'])
        except Exception:
            pass

    if 'submenu' in tables:
        sub_cols = [c['name'] for c in inspector.get_columns('submenu')]
        if 'is_deleted' not in sub_cols:
            op.add_column('submenu', sa.Column('is_deleted', sa.Boolean(), nullable=True))
        if 'created_at' not in sub_cols:
            op.add_column('submenu', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
        if 'updated_at' not in sub_cols:
            op.add_column('submenu', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

        sub_indexes = [idx['name'] for idx in inspector.get_indexes('submenu')]
        if 'ix_submenu_order_index' not in sub_indexes:
            op.create_index(op.f('ix_submenu_order_index'), 'submenu', ['order_index'], unique=False)

        sub_uqs = [uq['name'] for uq in inspector.get_unique_constraints('submenu')]
        if 'uq_submenu_path_per_menu' not in sub_uqs:
            try:
                op.create_unique_constraint('uq_submenu_path_per_menu', 'submenu', ['menu_id', 'path'])
            except Exception:
                pass
        if 'uq_submenu_title_per_menu' not in sub_uqs:
            try:
                op.create_unique_constraint('uq_submenu_title_per_menu', 'submenu', ['menu_id', 'title'])
            except Exception:
                pass


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'submenu' in tables:
        sub_uqs = [uq['name'] for uq in inspector.get_unique_constraints('submenu')]
        if 'uq_submenu_title_per_menu' in sub_uqs:
            op.drop_constraint('uq_submenu_title_per_menu', 'submenu', type_='unique')
        if 'uq_submenu_path_per_menu' in sub_uqs:
            op.drop_constraint('uq_submenu_path_per_menu', 'submenu', type_='unique')
        sub_indexes = [idx['name'] for idx in inspector.get_indexes('submenu')]
        if 'ix_submenu_order_index' in sub_indexes:
            op.drop_index(op.f('ix_submenu_order_index'), table_name='submenu')
        sub_cols = [c['name'] for c in inspector.get_columns('submenu')]
        if 'updated_at' in sub_cols:
            op.drop_column('submenu', 'updated_at')
        if 'created_at' in sub_cols:
            op.drop_column('submenu', 'created_at')
        if 'is_deleted' in sub_cols:
            op.drop_column('submenu', 'is_deleted')

    if 'menu' in tables:
        menu_indexes = [idx['name'] for idx in inspector.get_indexes('menu')]
        if 'ix_menu_order_index' in menu_indexes:
            op.drop_index(op.f('ix_menu_order_index'), table_name='menu')
        menu_cols = [c['name'] for c in inspector.get_columns('menu')]
        if 'updated_at' in menu_cols:
            op.drop_column('menu', 'updated_at')
        if 'created_at' in menu_cols:
            op.drop_column('menu', 'created_at')
        if 'is_deleted' in menu_cols:
            op.drop_column('menu', 'is_deleted')
        if 'order_index' in menu_cols:
            op.drop_column('menu', 'order_index')
