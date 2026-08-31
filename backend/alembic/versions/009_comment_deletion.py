"""Add is_deleted and deleted_at columns to social_comments table

Revision ID: 009_comment_deletion
Revises: 008_social_comment_replies
Create Date: 2026-08-31 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '009_comment_deletion'
down_revision: Union[str, None] = '008_social_comment_replies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [c['name'] for c in inspector.get_columns('social_comments')]
    indexes = [i['name'] for i in inspector.get_indexes('social_comments')]

    if 'is_deleted' not in existing_columns:
        op.add_column(
            'social_comments',
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false'))
        )

    if 'ix_social_comments_is_deleted' not in indexes:
        op.create_index(
            op.f('ix_social_comments_is_deleted'),
            'social_comments',
            ['is_deleted'],
            unique=False
        )

    if 'deleted_at' not in existing_columns:
        op.add_column(
            'social_comments',
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [c['name'] for c in inspector.get_columns('social_comments')]
    indexes = [i['name'] for i in inspector.get_indexes('social_comments')]

    if 'deleted_at' in existing_columns:
        op.drop_column('social_comments', 'deleted_at')

    if 'ix_social_comments_is_deleted' in indexes:
        op.drop_index(op.f('ix_social_comments_is_deleted'), table_name='social_comments')

    if 'is_deleted' in existing_columns:
        op.drop_column('social_comments', 'is_deleted')
