"""Update external_post_contexts foreign key constraint to ON DELETE CASCADE

Revision ID: 016_ext_post_ctx_cascade
Revises: 015_meta_ad_comments_rel
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016_ext_post_ctx_cascade'
down_revision = '015_meta_ad_comments_rel'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fks = inspector.get_foreign_keys('external_post_contexts')
    existing_fk_names = [fk['name'] for fk in fks if fk.get('name')]

    with op.batch_alter_table('external_post_contexts') as batch_op:
        for fk_name in existing_fk_names:
            if fk_name and ('social_account' in fk_name or 'social_accounts' in fk_name):
                batch_op.drop_constraint(fk_name, type_='foreignkey')

        batch_op.create_foreign_key(
            'fk_ext_post_contexts_social_account_id',
            'social_accounts',
            ['social_account_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fks = inspector.get_foreign_keys('external_post_contexts')
    existing_fk_names = [fk['name'] for fk in fks if fk.get('name')]

    with op.batch_alter_table('external_post_contexts') as batch_op:
        for fk_name in existing_fk_names:
            if fk_name and ('social_account' in fk_name or 'social_accounts' in fk_name):
                batch_op.drop_constraint(fk_name, type_='foreignkey')

        batch_op.create_foreign_key(
            'fk_external_post_contexts_social_account_id',
            'social_accounts',
            ['social_account_id'],
            ['id']
        )
