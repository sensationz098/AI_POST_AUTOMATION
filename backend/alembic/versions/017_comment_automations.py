"""Create automations and automation_executions tables for comment automation engine

Revision ID: 017_comment_automations
Revises: 016_ext_post_ctx_cascade
Create Date: 2026-09-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '017_comment_automations'
down_revision: Union[str, None] = '016_ext_post_ctx_cascade'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create automations table
    op.create_table(
        'automations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('social_account_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('post_target_type', sa.String(length=50), nullable=False, server_default='SPECIFIC_POST'),
        sa.Column('external_post_id', sa.String(length=255), nullable=True),
        sa.Column('internal_post_id', sa.Integer(), nullable=True),
        sa.Column('trigger_type', sa.String(length=50), nullable=False, server_default='ANY_COMMENT'),
        sa.Column('trigger_config', sa.JSON(), nullable=False),
        sa.Column('action_config', sa.JSON(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['social_account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['internal_post_id'], ['posts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automations_id'), 'automations', ['id'], unique=False)
    op.create_index(op.f('ix_automations_user_id'), 'automations', ['user_id'], unique=False)
    op.create_index(op.f('ix_automations_social_account_id'), 'automations', ['social_account_id'], unique=False)
    op.create_index(op.f('ix_automations_platform'), 'automations', ['platform'], unique=False)
    op.create_index(op.f('ix_automations_status'), 'automations', ['status'], unique=False)
    op.create_index(op.f('ix_automations_external_post_id'), 'automations', ['external_post_id'], unique=False)
    op.create_index(op.f('ix_automations_internal_post_id'), 'automations', ['internal_post_id'], unique=False)
    op.create_index('idx_automations_user_status', 'automations', ['user_id', 'status'], unique=False)
    op.create_index('idx_automations_account_post', 'automations', ['social_account_id', 'external_post_id', 'status'], unique=False)
    op.create_index('idx_automations_platform_status', 'automations', ['platform', 'status'], unique=False)

    # 2. Create automation_executions table
    op.create_table(
        'automation_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('automation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('social_account_id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=True),
        sa.Column('external_comment_id', sa.String(length=255), nullable=False),
        sa.Column('external_post_id', sa.String(length=255), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('contact_identifier', sa.String(length=255), nullable=True),
        sa.Column('contact_name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('trigger_result', sa.JSON(), nullable=True),
        sa.Column('public_reply_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('public_reply_result', sa.JSON(), nullable=True),
        sa.Column('private_message_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('private_message_result', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['automation_id'], ['automations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['social_account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['comment_id'], ['social_comments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('automation_id', 'external_comment_id', name='uq_automation_execution_comment')
    )
    op.create_index(op.f('ix_automation_executions_id'), 'automation_executions', ['id'], unique=False)
    op.create_index(op.f('ix_automation_executions_automation_id'), 'automation_executions', ['automation_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_user_id'), 'automation_executions', ['user_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_social_account_id'), 'automation_executions', ['social_account_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_comment_id'), 'automation_executions', ['comment_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_external_comment_id'), 'automation_executions', ['external_comment_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_external_post_id'), 'automation_executions', ['external_post_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_platform'), 'automation_executions', ['platform'], unique=False)
    op.create_index(op.f('ix_automation_executions_status'), 'automation_executions', ['status'], unique=False)
    op.create_index('idx_auto_exec_user_status', 'automation_executions', ['user_id', 'status'], unique=False)
    op.create_index('idx_auto_exec_created_at', 'automation_executions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_auto_exec_created_at', table_name='automation_executions')
    op.drop_index('idx_auto_exec_user_status', table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_status'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_platform'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_external_post_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_external_comment_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_comment_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_social_account_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_user_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_automation_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_id'), table_name='automation_executions')
    op.drop_table('automation_executions')

    op.drop_index('idx_automations_platform_status', table_name='automations')
    op.drop_index('idx_automations_account_post', table_name='automations')
    op.drop_index('idx_automations_user_status', table_name='automations')
    op.drop_index(op.f('ix_automations_internal_post_id'), table_name='automations')
    op.drop_index(op.f('ix_automations_external_post_id'), table_name='automations')
    op.drop_index(op.f('ix_automations_status'), table_name='automations')
    op.drop_index(op.f('ix_automations_platform'), table_name='automations')
    op.drop_index(op.f('ix_automations_social_account_id'), table_name='automations')
    op.drop_index(op.f('ix_automations_user_id'), table_name='automations')
    op.drop_index(op.f('ix_automations_id'), table_name='automations')
    op.drop_table('automations')
