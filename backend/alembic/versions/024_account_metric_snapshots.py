"""Create account_metric_snapshots table for historical account analytics

Revision ID: 024_account_metric_snapshots
Revises: 023_youtube_thumbnails
Create Date: 2026-09-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '024_account_metric_snapshots'
down_revision: Union[str, None] = '023_youtube_thumbnails'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'account_metric_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('social_account_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('followers_count', sa.Integer(), nullable=True),
        sa.Column('following_count', sa.Integer(), nullable=True),
        sa.Column('media_count', sa.Integer(), nullable=True),
        sa.Column('views_count', sa.BigInteger(), nullable=True),
        sa.Column('reach', sa.Integer(), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['social_account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('social_account_id', 'snapshot_date', name='uq_social_account_snapshot_date')
    )
    op.create_index('ix_account_metric_snapshots_id', 'account_metric_snapshots', ['id'], unique=False)
    op.create_index('ix_account_metric_snapshots_social_account_id', 'account_metric_snapshots', ['social_account_id'], unique=False)
    op.create_index('ix_account_metric_snapshots_snapshot_date', 'account_metric_snapshots', ['snapshot_date'], unique=False)
    op.create_index('idx_account_snapshots_account_date', 'account_metric_snapshots', ['social_account_id', 'snapshot_date'], unique=False)
    op.create_index('idx_account_snapshots_date', 'account_metric_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_account_snapshots_date', table_name='account_metric_snapshots')
    op.drop_index('idx_account_snapshots_account_date', table_name='account_metric_snapshots')
    op.drop_index('ix_account_metric_snapshots_snapshot_date', table_name='account_metric_snapshots')
    op.drop_index('ix_account_metric_snapshots_social_account_id', table_name='account_metric_snapshots')
    op.drop_index('ix_account_metric_snapshots_id', table_name='account_metric_snapshots')
    op.drop_table('account_metric_snapshots')
