"""add download_queue table

Revision ID: 005
Revises: 004
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create download_queue table for background download management.
    """
    op.create_table(
        'download_queue',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('spotify_id', sa.String(64), nullable=True),
        sa.Column('deezer_id', sa.String(64), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('artist', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_download_queue_status', 'download_queue', ['status'])
    op.create_index('idx_download_queue_spotify_id', 'download_queue', ['spotify_id'])
    op.create_index('idx_download_queue_priority', 'download_queue', ['priority', 'created_at'])


def downgrade() -> None:
    """
    Drop download_queue table.
    """
    op.drop_index('idx_download_queue_priority', table_name='download_queue')
    op.drop_index('idx_download_queue_spotify_id', table_name='download_queue')
    op.drop_index('idx_download_queue_status', table_name='download_queue')
    op.drop_table('download_queue')
