"""Add ig_username and fb_page_url to stories table

Revision ID: 021_story_urls
Revises: 020_story_platform_urls
Create Date: 2026-09-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '021_story_urls'
down_revision: Union[str, None] = '020_story_platform_urls'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stories', sa.Column('ig_username', sa.String(length=255), nullable=True))
    op.add_column('stories', sa.Column('fb_page_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('stories', 'fb_page_url')
    op.drop_column('stories', 'ig_username')
