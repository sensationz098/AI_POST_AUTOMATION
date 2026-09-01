"""Create meta_ads table for ad discovery and engagement object mapping

Revision ID: 012_meta_ads_engagement
Revises: 011_meta_ad_accounts
Create Date: 2026-09-01 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012_meta_ads_engagement'
down_revision = '011_meta_ad_accounts'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meta_ads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meta_ad_account_id', sa.String(length=255), nullable=False),
        sa.Column('ad_account_db_id', sa.Integer(), sa.ForeignKey('meta_ad_accounts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('meta_ad_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('campaign_id', sa.String(length=255), nullable=True),
        sa.Column('campaign_name', sa.String(length=255), nullable=True),
        sa.Column('adset_id', sa.String(length=255), nullable=True),
        sa.Column('adset_name', sa.String(length=255), nullable=True),
        sa.Column('effective_status', sa.String(length=50), nullable=True),
        sa.Column('configured_status', sa.String(length=50), nullable=True),
        sa.Column('creative_id', sa.String(length=255), nullable=True),
        sa.Column('facebook_page_id', sa.String(length=255), nullable=True),
        sa.Column('facebook_post_id', sa.String(length=255), nullable=True),
        sa.Column('instagram_account_id', sa.String(length=255), nullable=True),
        sa.Column('instagram_media_id', sa.String(length=255), nullable=True),
        sa.Column('engagement_object_type', sa.String(length=50), nullable=True),
        sa.Column('engagement_object_id', sa.String(length=255), nullable=True),
        sa.Column('mapping_status', sa.String(length=50), server_default='NOT_AVAILABLE', nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'meta_ad_id', name='uq_user_meta_ad')
    )
    op.create_index('ix_meta_ads_id', 'meta_ads', ['id'], unique=False)
    op.create_index('idx_meta_ads_user', 'meta_ads', ['user_id'], unique=False)
    op.create_index('idx_meta_ads_ad_account', 'meta_ads', ['meta_ad_account_id'], unique=False)
    op.create_index('idx_meta_ads_meta_ad_id', 'meta_ads', ['meta_ad_id'], unique=False)
    op.create_index('idx_meta_ads_fb_post', 'meta_ads', ['facebook_post_id'], unique=False)
    op.create_index('idx_meta_ads_ig_media', 'meta_ads', ['instagram_media_id'], unique=False)


def downgrade():
    op.drop_index('idx_meta_ads_ig_media', table_name='meta_ads')
    op.drop_index('idx_meta_ads_fb_post', table_name='meta_ads')
    op.drop_index('idx_meta_ads_meta_ad_id', table_name='meta_ads')
    op.drop_index('idx_meta_ads_ad_account', table_name='meta_ads')
    op.drop_index('idx_meta_ads_user', table_name='meta_ads')
    op.drop_index('ix_meta_ads_id', table_name='meta_ads')
    op.drop_table('meta_ads')
