"""Update external_post_contexts unique constraint to scope by social_account_id

Revision ID: 014_ext_post_account_scope
Revises: 013_external_post_context
Create Date: 2026-09-01 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014_ext_post_account_scope'
down_revision = '013_external_post_context'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Backfill social_account_id for any null records if matching social comment exists
    op.execute("""
        UPDATE external_post_contexts
        SET social_account_id = (
            SELECT sc.social_account_id
            FROM social_comments sc
            WHERE sc.external_post_id = external_post_contexts.external_post_id
              AND sc.platform = external_post_contexts.platform
              AND sc.social_account_id IS NOT NULL
            LIMIT 1
        )
        WHERE social_account_id IS NULL
    """)
    # 2. Delete any orphan records where social_account_id is still NULL
    op.execute("DELETE FROM external_post_contexts WHERE social_account_id IS NULL")

    # 3. Use batch alter table for SQLite and PostgreSQL safety
    with op.batch_alter_table('external_post_contexts') as batch_op:
        batch_op.drop_constraint('uq_ext_post_platform_ext_id', type_='unique')
        batch_op.alter_column('social_account_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint(
            'uq_ext_post_account_platform_ext_id',
            ['social_account_id', 'platform', 'external_post_id']
        )
        batch_op.create_index(
            'idx_ext_post_acc_plat_ext',
            ['social_account_id', 'platform', 'external_post_id'],
            unique=False
        )


def downgrade():
    with op.batch_alter_table('external_post_contexts') as batch_op:
        batch_op.drop_index('idx_ext_post_acc_plat_ext')
        batch_op.drop_constraint('uq_ext_post_account_platform_ext_id', type_='unique')
        batch_op.alter_column('social_account_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_unique_constraint(
            'uq_ext_post_platform_ext_id',
            ['platform', 'external_post_id']
        )
