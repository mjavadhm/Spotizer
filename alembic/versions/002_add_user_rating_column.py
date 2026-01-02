"""add user_rating column to user_downloads

Revision ID: 002
Revises: 001
Create Date: 2026-01-02 03:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add user_rating column for like/dislike functionality.
    Values: 1=like, -1=dislike, NULL=no rating
    """
    op.add_column('user_downloads', sa.Column('user_rating', sa.Integer(), nullable=True))


def downgrade() -> None:
    """
    Remove user_rating column.
    """
    op.drop_column('user_downloads', 'user_rating')
