"""Create youtube_uploads table for resumable video upload lifecycle

Revision ID: 022_youtube_uploads
Revises: 021_story_urls
Create Date: 2026-09-10

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '022_youtube_uploads'
down_revision: Union[str, None] = '021_story_urls'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'youtube_uploads',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('upload_id', sa.String(length=100), unique=True, nullable=False, index=True),
        sa.Column('client_mutation_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('social_account_id', sa.Integer(), sa.ForeignKey('social_accounts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('channel_id', sa.String(length=255), nullable=False),
        sa.Column('video_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('privacy_status', sa.String(length=50), server_default='private', nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=100), server_default='video/mp4', nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('bytes_uploaded', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('progress_percentage', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('upload_status', sa.String(length=50), server_default='INITIATED', nullable=False, index=True),
        sa.Column('processing_status', sa.String(length=50), nullable=True),
        sa.Column('processing_failure_reason', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('encrypted_session_url', sa.Text(), nullable=True),
        sa.Column('video_url', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    op.create_index('idx_yt_uploads_user', 'youtube_uploads', ['user_id'])
    op.create_index('idx_yt_uploads_account', 'youtube_uploads', ['social_account_id'])
    op.create_index('idx_yt_uploads_status', 'youtube_uploads', ['upload_status'])
    op.create_unique_constraint('uq_youtube_uploads_user_mutation', 'youtube_uploads', ['user_id', 'client_mutation_id'])


def downgrade() -> None:
    op.drop_constraint('uq_youtube_uploads_user_mutation', 'youtube_uploads', type_='unique')
    op.drop_index('idx_yt_uploads_status', table_name='youtube_uploads')
    op.drop_index('idx_yt_uploads_account', table_name='youtube_uploads')
    op.drop_index('idx_yt_uploads_user', table_name='youtube_uploads')
    op.drop_table('youtube_uploads')
