"""add quality to user_content_unique constraint

Revision ID: 001
Revises: 
Create Date: 2026-01-02 01:34:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add quality field to the user_content_unique constraint.
    This allows users to cache the same content in different qualities.
    """
    # Drop old constraint
    op.drop_constraint('user_content_unique', 'user_downloads', type_='unique')
    
    # Create new constraint with quality field
    op.create_unique_constraint(
        'user_content_unique',
        'user_downloads',
        ['user_id', 'deezer_id', 'content_type', 'quality']
    )


def downgrade() -> None:
    """
    Rollback: Remove quality from the constraint.
    WARNING: This may cause data loss if you have duplicate content in different qualities!
    """
    # Drop new constraint
    op.drop_constraint('user_content_unique', 'user_downloads', type_='unique')
    
    # Recreate old constraint without quality
    op.create_unique_constraint(
        'user_content_unique',
        'user_downloads',
        ['user_id', 'deezer_id', 'content_type']
    )
