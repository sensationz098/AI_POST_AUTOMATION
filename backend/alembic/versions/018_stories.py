"""Create stories table for Instagram and Facebook Stories automation

Revision ID: 018_stories
Revises: 017_comment_automations
Create Date: 2026-09-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '018_stories'
down_revision: Union[str, None] = '017_comment_automations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create stories table
    op.create_table(
        'stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('media_url', sa.Text(), nullable=False),
        sa.Column('media_type', sa.String(length=50), nullable=False, server_default='image'),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('platforms', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('fb_story_id', sa.String(length=255), nullable=True),
        sa.Column('ig_container_id', sa.String(length=255), nullable=True),
        sa.Column('ig_story_id', sa.String(length=255), nullable=True),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brand_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create single-column indexes
    op.create_index(op.f('ix_stories_id'), 'stories', ['id'], unique=False)
    op.create_index(op.f('ix_stories_brand_id'), 'stories', ['brand_id'], unique=False)
    op.create_index(op.f('ix_stories_user_id'), 'stories', ['user_id'], unique=False)
    op.create_index(op.f('ix_stories_status'), 'stories', ['status'], unique=False)
    op.create_index(op.f('ix_stories_scheduled_at'), 'stories', ['scheduled_at'], unique=False)

    # 3. Create composite indexes
    op.create_index('idx_stories_user_status', 'stories', ['user_id', 'status'], unique=False)
    op.create_index('idx_stories_brand_status', 'stories', ['brand_id', 'status'], unique=False)
    op.create_index('idx_stories_scheduled', 'stories', ['scheduled_at', 'status'], unique=False)


def downgrade() -> None:
    # 1. Drop composite indexes
    op.drop_index('idx_stories_scheduled', table_name='stories')
    op.drop_index('idx_stories_brand_status', table_name='stories')
    op.drop_index('idx_stories_user_status', table_name='stories')

    # 2. Drop single-column indexes
    op.drop_index(op.f('ix_stories_scheduled_at'), table_name='stories')
    op.drop_index(op.f('ix_stories_status'), table_name='stories')
    op.drop_index(op.f('ix_stories_user_id'), table_name='stories')
    op.drop_index(op.f('ix_stories_brand_id'), table_name='stories')
    op.drop_index(op.f('ix_stories_id'), table_name='stories')

    # 3. Drop table
    op.drop_table('stories')
