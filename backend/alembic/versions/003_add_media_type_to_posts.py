"""Add nullable media_type column to posts table

Revision ID: 003_add_media_type_to_posts
Revises: 002_production_hardening
Create Date: 2026-08-21 12:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_media_type_to_posts'
down_revision: Union[str, None] = '002_production_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add nullable media_type column to posts table safely without dropping or altering existing data
    op.add_column(
        'posts',
        sa.Column('media_type', sa.String(length=50), nullable=True)
    )

def downgrade() -> None:
    # Remove media_type column cleanly on rollback
    op.drop_column('posts', 'media_type')
