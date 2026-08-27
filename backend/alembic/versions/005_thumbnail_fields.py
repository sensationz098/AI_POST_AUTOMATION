"""Add nullable video thumbnail columns to posts table

Revision ID: 005_thumbnail_fields
Revises: 004_auth_refresh_tokens
Create Date: 2026-08-27 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_thumbnail_fields'
down_revision: Union[str, None] = '004_auth_refresh_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable thumbnail columns to posts table safely without affecting existing posts
    op.add_column('posts', sa.Column('thumbnail_url', sa.Text(), nullable=True))
    op.add_column('posts', sa.Column('thumbnail_type', sa.String(length=50), nullable=True, server_default='NONE'))
    op.add_column('posts', sa.Column('thumbnail_offset_ms', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove thumbnail columns cleanly on rollback
    op.drop_column('posts', 'thumbnail_offset_ms')
    op.drop_column('posts', 'thumbnail_type')
    op.drop_column('posts', 'thumbnail_url')
