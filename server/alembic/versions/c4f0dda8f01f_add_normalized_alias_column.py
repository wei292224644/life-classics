"""add normalized_alias column

Revision ID: c4f0dda8f01f
Revises: 4212f0c676ef
Create Date: 2026-03-31 22:20:15.126005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f0dda8f01f'
down_revision: Union[str, Sequence[str], None] = '4212f0c676ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('ingredient_aliases', sa.Column('normalized_alias', sa.String(length=255), nullable=False))
    op.create_unique_constraint(None, 'ingredient_aliases', ['normalized_alias'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'ingredient_aliases', type_='unique')
    op.drop_column('ingredient_aliases', 'normalized_alias')
