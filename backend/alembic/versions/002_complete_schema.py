"""Complete Schema and Constraints Migration for PostgreSQL

Revision ID: 002_complete_schema
Revises: 001_production_hardening
Create Date: 2026-08-12 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_complete_schema'
down_revision: Union[str, None] = '001_production_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='Editor'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True, if_not_exists=True)

    # 2. Brand Profiles Table
    op.create_table(
        'brand_profiles',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('brand_colors', sa.JSON(), nullable=True),
        sa.Column('tone_of_voice', sa.String(length=255), nullable=True),
        sa.Column('target_audience', sa.Text(), nullable=True),
        sa.Column('cta_style', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('ix_brand_profiles_user_id', 'brand_profiles', ['user_id'], if_not_exists=True)

    # 3. Meta Accounts Table
    op.create_table(
        'meta_accounts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brand_profiles.id'), nullable=False, unique=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('facebook_page_id', sa.String(length=255), nullable=True),
        sa.Column('facebook_page_name', sa.String(length=255), nullable=True),
        sa.Column('instagram_account_id', sa.String(length=255), nullable=True),
        sa.Column('instagram_username', sa.String(length=255), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('is_connected', sa.Boolean(), server_default='false'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )

    # 4. Social Accounts Table
    op.create_table(
        'social_accounts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brand_profiles.id'), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('account_id', sa.String(length=255), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('token_type', sa.String(length=100), server_default='page_access_token'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='CONNECTED'),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('idx_accounts_user_platform', 'social_accounts', ['user_id', 'platform'], if_not_exists=True)
    op.create_index('idx_accounts_status', 'social_accounts', ['status'], if_not_exists=True)

    # 5. Posts Table
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('cta', sa.String(length=255), nullable=True),
        sa.Column('seo_keywords', sa.JSON(), nullable=True),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=1000), nullable=True),
        sa.Column('platforms', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='DRAFT'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('max_retries', sa.Integer(), server_default='3'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('fb_post_id', sa.String(length=255), nullable=True),
        sa.Column('ig_container_id', sa.String(length=255), nullable=True),
        sa.Column('ig_media_id', sa.String(length=255), nullable=True),
        sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brand_profiles.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('idx_posts_user_status', 'posts', ['user_id', 'status'], if_not_exists=True)
    op.create_index('idx_posts_brand_status', 'posts', ['brand_id', 'status'], if_not_exists=True)
    op.create_index('idx_posts_scheduled', 'posts', ['scheduled_at', 'status'], if_not_exists=True)

    # 6. Publishing Batches Table
    op.create_table(
        'publishing_batches',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), unique=True, nullable=True),
        sa.Column('status', sa.String(length=50), server_default='QUEUED'),
        sa.Column('total_targets', sa.Integer(), server_default='0'),
        sa.Column('successful_targets', sa.Integer(), server_default='0'),
        sa.Column('failed_targets', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('idx_batches_user_status', 'publishing_batches', ['user_id', 'status'], if_not_exists=True)

    # 7. Publishing Jobs Table
    op.create_table(
        'publishing_jobs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('batch_id', sa.Integer(), sa.ForeignKey('publishing_batches.id'), nullable=False),
        sa.Column('social_account_id', sa.Integer(), sa.ForeignKey('social_accounts.id'), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='QUEUED'),
        sa.Column('external_post_id', sa.String(length=255), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0'),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('idx_jobs_batch_status', 'publishing_jobs', ['batch_id', 'status'], if_not_exists=True)
    op.create_index('idx_jobs_account_status', 'publishing_jobs', ['social_account_id', 'status'], if_not_exists=True)

    # 8. Post Analytics Table
    op.create_table(
        'post_analytics',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('posts.id'), nullable=False, unique=True),
        sa.Column('likes', sa.Integer(), server_default='0'),
        sa.Column('comments', sa.Integer(), server_default='0'),
        sa.Column('shares', sa.Integer(), server_default='0'),
        sa.Column('saves', sa.Integer(), server_default='0'),
        sa.Column('reach', sa.Integer(), server_default='0'),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('engagement_rate', sa.Float(), server_default='0.0'),
        sa.Column('follower_growth', sa.Integer(), server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )

    # 9. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'], if_not_exists=True)

def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('post_analytics')
    op.drop_table('publishing_jobs')
    op.drop_table('publishing_batches')
    op.drop_table('posts')
    op.drop_table('social_accounts')
    op.drop_table('meta_accounts')
    op.drop_table('brand_profiles')
    op.drop_table('users')
