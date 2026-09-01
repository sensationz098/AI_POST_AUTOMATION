"""Add ON DELETE CASCADE constraint to publishing_jobs.social_account_id foreign key

Revision ID: 010_pub_job_account_cascade
Revises: 009_comment_deletion
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '010_pub_job_account_cascade'
down_revision: Union[str, None] = '009_comment_deletion'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    fk_constraints = inspector.get_foreign_keys('publishing_jobs')
    for fk in fk_constraints:
        if 'social_account_id' in fk.get('constrained_columns', []):
            fk_name = fk.get('name')
            if fk_name:
                op.drop_constraint(fk_name, 'publishing_jobs', type_='foreignkey')

    op.create_foreign_key(
        'fk_publishing_jobs_social_account_id',
        'publishing_jobs',
        'social_accounts',
        ['social_account_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    fk_constraints = inspector.get_foreign_keys('publishing_jobs')
    for fk in fk_constraints:
        if 'social_account_id' in fk.get('constrained_columns', []):
            fk_name = fk.get('name')
            if fk_name:
                op.drop_constraint(fk_name, 'publishing_jobs', type_='foreignkey')

    op.create_foreign_key(
        'publishing_jobs_social_account_id_fkey',
        'publishing_jobs',
        'social_accounts',
        ['social_account_id'],
        ['id']
    )
