"""add description to series

Revision ID: c3d9a1f2b847
Revises: ef9f640902c4
Create Date: 2026-11-24 20:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d9a1f2b847'
down_revision: Union[str, None] = 'ef9f640902c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('series', sa.Column('description', sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column('series', 'description')
