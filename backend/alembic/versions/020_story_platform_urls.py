"""Add fb_story_url and ig_story_url to stories table
 
Revision ID: 020_story_platform_urls
Revises: 019_story_target_accounts
Create Date: 2026-09-09
 
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
 
# revision identifiers, used by Alembic.
revision: str = '020_story_platform_urls'
down_revision: Union[str, None] = '019_story_target_accounts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
 
 
def upgrade() -> None:
    op.add_column('stories', sa.Column('fb_story_url', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('ig_story_url', sa.Text(), nullable=True))
 
 
def downgrade() -> None:
    op.drop_column('stories', 'ig_story_url')
    op.drop_column('stories', 'fb_story_url')
