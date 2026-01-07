"""add spotify_id to tracks

Revision ID: 004
Revises: 003
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add spotify_id column to tracks table.
    This allows linking Spotify search results to downloaded Deezer tracks.
    """
    op.add_column('tracks', sa.Column('spotify_id', sa.String(64), nullable=True))
    op.create_index('idx_tracks_spotify_id', 'tracks', ['spotify_id'])


def downgrade() -> None:
    """
    Remove spotify_id column from tracks table.
    """
    op.drop_index('idx_tracks_spotify_id', table_name='tracks')
    op.drop_column('tracks', 'spotify_id')
