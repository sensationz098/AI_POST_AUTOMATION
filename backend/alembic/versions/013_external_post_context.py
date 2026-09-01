"""Create external_post_contexts table for caching non-app post metadata

Revision ID: 013_external_post_context
Revises: 012_meta_ads_engagement
Create Date: 2026-09-01 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013_external_post_context'
down_revision = '012_meta_ads_engagement'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'external_post_contexts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('social_account_id', sa.Integer(), sa.ForeignKey('social_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('external_post_id', sa.String(length=255), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=True),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('permalink', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'external_post_id', name='uq_ext_post_platform_ext_id')
    )
    op.create_index('ix_external_post_contexts_id', 'external_post_contexts', ['id'], unique=False)
    op.create_index('idx_ext_post_platform', 'external_post_contexts', ['platform'], unique=False)
    op.create_index('idx_ext_post_account', 'external_post_contexts', ['social_account_id'], unique=False)
    op.create_index('idx_ext_post_ext_id', 'external_post_contexts', ['external_post_id'], unique=False)


def downgrade():
    op.drop_index('idx_ext_post_ext_id', table_name='external_post_contexts')
    op.drop_index('idx_ext_post_account', table_name='external_post_contexts')
    op.drop_index('idx_ext_post_platform', table_name='external_post_contexts')
    op.drop_index('ix_external_post_contexts_id', table_name='external_post_contexts')
    op.drop_table('external_post_contexts')
