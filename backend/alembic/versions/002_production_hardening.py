"""Production Hardening Initial Migration

Revision ID: 002_production_hardening
Revises: 001_complete_schema
Create Date: 2026-08-12 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_production_hardening'
down_revision: Union[str, None] = '001_complete_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Ensure indexes exist on users table
    op.create_index('ix_users_email', 'users', ['email'], unique=True, if_not_exists=True)
    
    # Ensure indexes exist on social_accounts table
    op.create_index('ix_social_accounts_user_platform', 'social_accounts', ['user_id', 'platform'], if_not_exists=True)
    op.create_index('ix_social_accounts_user_account_id', 'social_accounts', ['user_id', 'platform', 'account_id'], unique=True, if_not_exists=True)

    # Ensure indexes exist on posts table
    op.create_index('ix_posts_user_status', 'posts', ['user_id', 'status'], if_not_exists=True)
    op.create_index('ix_posts_scheduled_at', 'posts', ['scheduled_at'], if_not_exists=True)

    # Ensure indexes exist on publishing_jobs table
    op.create_index('ix_publishing_jobs_batch_status', 'publishing_jobs', ['batch_id', 'status'], if_not_exists=True)

def downgrade() -> None:
    op.drop_index('ix_publishing_jobs_batch_status', table_name='publishing_jobs', if_exists=True)
    op.drop_index('ix_posts_scheduled_at', table_name='posts', if_exists=True)
    op.drop_index('ix_posts_user_status', table_name='posts', if_exists=True)
    op.drop_index('ix_social_accounts_user_account_id', table_name='social_accounts', if_exists=True)
    op.drop_index('ix_social_accounts_user_platform', table_name='social_accounts', if_exists=True)
    op.drop_index('ix_users_email', table_name='users', if_exists=True)
