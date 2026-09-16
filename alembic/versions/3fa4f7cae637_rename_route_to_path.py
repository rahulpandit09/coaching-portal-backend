"""rename route to path

Revision ID: 3fa4f7cae637
Revises: 
Create Date: 2026-07-10 13:22:52.655023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fa4f7cae637'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'menu' in tables:
        menu_cols = [c['name'] for c in inspector.get_columns('menu')]
        if 'path' not in menu_cols:
            op.add_column('menu', sa.Column('path', sa.String(length=100), nullable=True))
        if 'route' in menu_cols:
            op.drop_column('menu', 'route')

    if 'submenus' in tables:
        submenu_cols = [c['name'] for c in inspector.get_columns('submenus')]
        if 'path' not in submenu_cols:
            op.add_column('submenus', sa.Column('path', sa.String(), nullable=True))
        if 'route' in submenu_cols:
            op.drop_column('submenus', 'route')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'submenus' in tables:
        submenu_cols = [c['name'] for c in inspector.get_columns('submenus')]
        if 'route' not in submenu_cols:
            op.add_column('submenus', sa.Column('route', sa.VARCHAR(), autoincrement=False, nullable=True))
        if 'path' in submenu_cols:
            op.drop_column('submenus', 'path')

    if 'menu' in tables:
        menu_cols = [c['name'] for c in inspector.get_columns('menu')]
        if 'route' not in menu_cols:
            op.add_column('menu', sa.Column('route', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
        if 'path' in menu_cols:
            op.drop_column('menu', 'path')
