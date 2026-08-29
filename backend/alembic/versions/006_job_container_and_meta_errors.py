"""Add ig_container_id and raw Meta error columns to publishing_jobs table

Revision ID: 006_job_container_and_meta_errors
Revises: 005_thumbnail_fields
Create Date: 2026-08-29 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_job_container_and_meta_errors'
down_revision: Union[str, None] = '005_thumbnail_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ig_container_id and Meta error metadata columns safely to publishing_jobs table
    op.add_column('publishing_jobs', sa.Column('ig_container_id', sa.String(length=255), nullable=True))
    op.add_column('publishing_jobs', sa.Column('meta_status_code', sa.Integer(), nullable=True))
    op.add_column('publishing_jobs', sa.Column('meta_error_code', sa.Integer(), nullable=True))
    op.add_column('publishing_jobs', sa.Column('meta_error_subcode', sa.Integer(), nullable=True))
    op.add_column('publishing_jobs', sa.Column('meta_error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    # Drop added columns on rollback
    op.drop_column('publishing_jobs', 'meta_error_message')
    op.drop_column('publishing_jobs', 'meta_error_subcode')
    op.drop_column('publishing_jobs', 'meta_error_code')
    op.drop_column('publishing_jobs', 'meta_status_code')
    op.drop_column('publishing_jobs', 'ig_container_id')
