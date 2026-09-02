"""Add meta_ad_id to social_comments table

Revision ID: 015_meta_ad_comments_relationship
Revises: 014_external_post_context_account_scope
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_meta_ad_comments_relationship'
down_revision = '014_external_post_context_account_scope'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('social_comments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('meta_ad_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_social_comments_meta_ad_id'), ['meta_ad_id'], unique=False)
        batch_op.create_foreign_key('fk_social_comments_meta_ad_id', 'meta_ads', ['meta_ad_id'], ['id'], ondelete='SET NULL')

def downgrade():
    with op.batch_alter_table('social_comments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_social_comments_meta_ad_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_social_comments_meta_ad_id'))
        batch_op.drop_column('meta_ad_id')
