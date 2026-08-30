"""Create social_comment_replies table for manual comment reply audit history

Revision ID: 008_social_comment_replies
Revises: 007_social_comments
Create Date: 2026-08-30 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_social_comment_replies'
down_revision: Union[str, None] = '007_social_comments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'social_comment_replies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('external_reply_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['social_comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_social_comment_replies_comment_id'), 'social_comment_replies', ['comment_id'], unique=False)
    op.create_index(op.f('ix_social_comment_replies_id'), 'social_comment_replies', ['id'], unique=False)
    op.create_index(op.f('ix_social_comment_replies_platform'), 'social_comment_replies', ['platform'], unique=False)
    op.create_index(op.f('ix_social_comment_replies_status'), 'social_comment_replies', ['status'], unique=False)
    op.create_index(op.f('ix_social_comment_replies_user_id'), 'social_comment_replies', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_social_comment_replies_user_id'), table_name='social_comment_replies')
    op.drop_index(op.f('ix_social_comment_replies_status'), table_name='social_comment_replies')
    op.drop_index(op.f('ix_social_comment_replies_platform'), table_name='social_comment_replies')
    op.drop_index(op.f('ix_social_comment_replies_id'), table_name='social_comment_replies')
    op.drop_index(op.f('ix_social_comment_replies_comment_id'), table_name='social_comment_replies')
    op.drop_table('social_comment_replies')
