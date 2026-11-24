"""add tmdb_id to series

Revision ID: d4e5f6a7b8c9
Revises: c3d9a1f2b847
Create Date: 2026-11-24 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d9a1f2b847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('series', sa.Column('tmdb_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_series_tmdb_id'), 'series', ['tmdb_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_series_tmdb_id'), table_name='series')
    op.drop_column('series', 'tmdb_id')
