"""add channel_id and message_id to tracks

Revision ID: 003
Revises: 002
Create Date: 2026-01-07 21:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add channel_id and message_id columns to tracks table.
    These are used for streaming tracks from a Telegram channel.
    """
    op.add_column('tracks', sa.Column('channel_id', sa.BigInteger(), nullable=True))
    op.add_column('tracks', sa.Column('message_id', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """
    Remove channel_id and message_id columns from tracks table.
    """
    op.drop_column('tracks', 'message_id')
    op.drop_column('tracks', 'channel_id')
