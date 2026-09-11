"""Add thumbnail columns to youtube_uploads table

Revision ID: 023_youtube_thumbnails
Revises: 022_youtube_uploads
Create Date: 2026-09-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '023_youtube_thumbnails'
down_revision: Union[str, None] = '022_youtube_uploads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('youtube_uploads', sa.Column('thumbnail_url', sa.Text(), nullable=True))
    op.add_column('youtube_uploads', sa.Column('thumbnail_status', sa.String(length=50), nullable=True))
    op.add_column('youtube_uploads', sa.Column('thumbnail_error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('youtube_uploads', 'thumbnail_error')
    op.drop_column('youtube_uploads', 'thumbnail_status')
    op.drop_column('youtube_uploads', 'thumbnail_url')
