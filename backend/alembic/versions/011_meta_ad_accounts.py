"""Create meta_ad_accounts table

Revision ID: 011_meta_ad_accounts
Revises: 010_pub_job_account_cascade
Create Date: 2026-09-01 14:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_meta_ad_accounts'
down_revision = '010_pub_job_account_cascade'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meta_ad_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meta_ad_account_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('account_status', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('timezone_name', sa.String(length=100), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'meta_ad_account_id', name='uq_user_meta_ad_account')
    )
    op.create_index('ix_meta_ad_accounts_id', 'meta_ad_accounts', ['id'], unique=False)
    op.create_index('idx_meta_ad_accounts_user', 'meta_ad_accounts', ['user_id'], unique=False)
    op.create_index('idx_meta_ad_accounts_account_id', 'meta_ad_accounts', ['meta_ad_account_id'], unique=False)


def downgrade():
    op.drop_index('idx_meta_ad_accounts_account_id', table_name='meta_ad_accounts')
    op.drop_index('idx_meta_ad_accounts_user', table_name='meta_ad_accounts')
    op.drop_index('ix_meta_ad_accounts_id', table_name='meta_ad_accounts')
    op.drop_table('meta_ad_accounts')
