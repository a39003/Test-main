"""add_todo_performance_indexes

Revision ID: b1820d9e8314
Revises: a0790c76a129
Create Date: 2026-09-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1820d9e8314'
down_revision: Union[str, None] = 'a0790c76a129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for user-filtered queries and ordering by created_at
    op.create_index(
        'ix_todos_user_id_created_at',
        'todos',
        ['user_id', 'created_at'],
        unique=False,
    )
    # Composite index for status filtering, user scoping, and sorting
    op.create_index(
        'ix_todos_user_id_completed_created_at',
        'todos',
        ['user_id', 'completed', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_todos_user_id_completed_created_at', table_name='todos')
    op.drop_index('ix_todos_user_id_created_at', table_name='todos')
