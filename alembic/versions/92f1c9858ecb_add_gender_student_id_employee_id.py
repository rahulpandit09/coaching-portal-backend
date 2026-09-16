"""add gender student id employee id

Revision ID: 92f1c9858ecb
Revises: e7a1b6d04a30
Create Date: 2026-09-16 22:20:18.149035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92f1c9858ecb'
down_revision: Union[str, Sequence[str], None] = 'e7a1b6d04a30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'student_details' in tables:
        student_uqs = [uq['name'] for uq in inspector.get_unique_constraints('student_details')]
        if 'student_details_student_id_key' in student_uqs:
            op.drop_constraint('student_details_student_id_key', 'student_details', type_='unique')
        student_idx = [idx['name'] for idx in inspector.get_indexes('student_details')]
        if 'ix_student_details_student_id' not in student_idx:
            op.create_index(op.f('ix_student_details_student_id'), 'student_details', ['student_id'], unique=True)

    if 'teacher_details' in tables:
        teacher_uqs = [uq['name'] for uq in inspector.get_unique_constraints('teacher_details')]
        if 'teacher_details_employee_id_key' in teacher_uqs:
            op.drop_constraint('teacher_details_employee_id_key', 'teacher_details', type_='unique')
        teacher_idx = [idx['name'] for idx in inspector.get_indexes('teacher_details')]
        if 'ix_teacher_details_employee_id' not in teacher_idx:
            op.create_index(op.f('ix_teacher_details_employee_id'), 'teacher_details', ['employee_id'], unique=True)

    if 'users' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'gender' not in user_cols:
            op.add_column('users', sa.Column('gender', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'users' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'gender' in user_cols:
            op.drop_column('users', 'gender')

    if 'teacher_details' in tables:
        teacher_idx = [idx['name'] for idx in inspector.get_indexes('teacher_details')]
        if 'ix_teacher_details_employee_id' in teacher_idx:
            op.drop_index(op.f('ix_teacher_details_employee_id'), table_name='teacher_details')
        teacher_uqs = [uq['name'] for uq in inspector.get_unique_constraints('teacher_details')]
        if 'teacher_details_employee_id_key' not in teacher_uqs:
            try:
                op.create_unique_constraint('teacher_details_employee_id_key', 'teacher_details', ['employee_id'])
            except Exception:
                pass

    if 'student_details' in tables:
        student_idx = [idx['name'] for idx in inspector.get_indexes('student_details')]
        if 'ix_student_details_student_id' in student_idx:
            op.drop_index(op.f('ix_student_details_student_id'), table_name='student_details')
        student_uqs = [uq['name'] for uq in inspector.get_unique_constraints('student_details')]
        if 'student_details_student_id_key' not in student_uqs:
            try:
                op.create_unique_constraint('student_details_student_id_key', 'student_details', ['student_id'])
            except Exception:
                pass
