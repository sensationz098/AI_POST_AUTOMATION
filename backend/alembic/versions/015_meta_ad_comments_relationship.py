"""Add meta_ad_id to social_comments table

Revision ID: 015_meta_ad_comments_rel
Revises: 014_ext_post_account_scope
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_meta_ad_comments_rel'
down_revision = '014_ext_post_account_scope'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col['name'] for col in inspector.get_columns('social_comments')]
    column_exists = 'meta_ad_id' in columns

    indexes = [idx['name'] for idx in inspector.get_indexes('social_comments')]
    index_exists = 'ix_social_comments_meta_ad_id' in indexes

    fks = inspector.get_foreign_keys('social_comments')
    fk_exists = any('meta_ad_id' in fk.get('constrained_columns', []) for fk in fks)

    with op.batch_alter_table('social_comments', schema=None) as batch_op:
        if not column_exists:
            batch_op.add_column(sa.Column('meta_ad_id', sa.Integer(), nullable=True))
        if not index_exists:
            batch_op.create_index(batch_op.f('ix_social_comments_meta_ad_id'), ['meta_ad_id'], unique=False)
        if not fk_exists:
            batch_op.create_foreign_key('fk_social_comments_meta_ad_id', 'meta_ads', ['meta_ad_id'], ['id'], ondelete='SET NULL')

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col['name'] for col in inspector.get_columns('social_comments')]
    column_exists = 'meta_ad_id' in columns

    indexes = [idx['name'] for idx in inspector.get_indexes('social_comments')]
    index_exists = 'ix_social_comments_meta_ad_id' in indexes

    fks = inspector.get_foreign_keys('social_comments')

    with op.batch_alter_table('social_comments', schema=None) as batch_op:
        if fks:
            for fk in fks:
                if 'meta_ad_id' in fk.get('constrained_columns', []):
                    fk_name = fk.get('name') or 'fk_social_comments_meta_ad_id'
                    batch_op.drop_constraint(fk_name, type_='foreignkey')
        if index_exists:
            batch_op.drop_index(batch_op.f('ix_social_comments_meta_ad_id'))
        if column_exists:
            batch_op.drop_column('meta_ad_id')
