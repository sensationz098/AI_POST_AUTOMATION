"""Add target_account_ids to stories table

Revision ID: 019_story_target_accounts
Revises: 018_stories
Create Date: 2026-09-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '019_story_target_accounts'
down_revision: Union[str, None] = '018_stories'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stories', sa.Column('target_account_ids', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('stories', 'target_account_ids')
