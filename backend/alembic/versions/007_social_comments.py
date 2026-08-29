"""Create social_comments table for Meta comment webhook ingestion

Revision ID: 007_social_comments
Revises: 006_job_meta_errors
Create Date: 2026-08-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_social_comments'
down_revision: Union[str, None] = '006_job_meta_errors'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'social_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('social_account_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('external_comment_id', sa.String(length=255), nullable=False),
        sa.Column('external_post_id', sa.String(length=255), nullable=True),
        sa.Column('parent_comment_id', sa.String(length=255), nullable=True),
        sa.Column('comment_text', sa.Text(), nullable=True),
        sa.Column('commenter_id', sa.String(length=255), nullable=True),
        sa.Column('commenter_name', sa.String(length=255), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_object', sa.String(length=50), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='RECEIVED'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['social_account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'external_comment_id', name='uq_social_comment_platform_ext_id')
    )
    op.create_index(op.f('ix_social_comments_external_comment_id'), 'social_comments', ['external_comment_id'], unique=False)
    op.create_index(op.f('ix_social_comments_external_post_id'), 'social_comments', ['external_post_id'], unique=False)
    op.create_index(op.f('ix_social_comments_id'), 'social_comments', ['id'], unique=False)
    op.create_index(op.f('ix_social_comments_platform'), 'social_comments', ['platform'], unique=False)
    op.create_index(op.f('ix_social_comments_processing_status'), 'social_comments', ['processing_status'], unique=False)
    op.create_index(op.f('ix_social_comments_social_account_id'), 'social_comments', ['social_account_id'], unique=False)
    op.create_index(op.f('ix_social_comments_user_id'), 'social_comments', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_social_comments_user_id'), table_name='social_comments')
    op.drop_index(op.f('ix_social_comments_social_account_id'), table_name='social_comments')
    op.drop_index(op.f('ix_social_comments_processing_status'), table_name='social_comments')
    op.drop_index(op.f('ix_social_comments_platform'), table_name='social_comments')
    op.drop_index(op.f('ix_social_comments_id'), table_name='social_comments')
    op.drop_index(op.f('ix_social_comments_external_post_id'), table_name='social_comments')
    op.drop_index(op.f('ix_social_comments_external_comment_id'), table_name='social_comments')
    op.drop_table('social_comments')
