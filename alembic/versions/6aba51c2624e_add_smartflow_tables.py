"""Add SmartFlow tables

Revision ID: 6aba51c2624e
Revises: 034
Create Date: 2026-03-05 11:40:08.633539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aba51c2624e'
down_revision: Union[str, None] = '034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SmartFlow Configuration Table
    op.create_table(
        'smartflow_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('webhook_urls', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('buy_threshold', sa.Float(), nullable=False, server_default='4.0'),
        sa.Column('sell_threshold', sa.Float(), nullable=False, server_default='-4.0'),
        sa.Column('close_threshold', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('score_window_minutes', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('update_interval_seconds', sa.Integer(), nullable=False, server_default='45'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('user_id')
    )

    # SmartFlow Signal Logs Table
    op.create_table(
        'smartflow_signal_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('bullish_flows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('bearish_flows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_premium', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('webhooks_posted', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('post_successful', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('post_errors', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['smartflow_config.id'], ondelete='CASCADE')
    )
    op.create_index('idx_smartflow_logs_ticker', 'smartflow_signal_logs', ['ticker'])
    op.create_index('idx_smartflow_logs_created', 'smartflow_signal_logs', ['created_at'])

    # SmartFlow Score History Table
    op.create_table(
        'smartflow_score_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('bullish_flows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('bearish_flows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_premium', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_smartflow_history_ticker', 'smartflow_score_history', ['ticker'])
    op.create_index('idx_smartflow_history_timestamp', 'smartflow_score_history', ['timestamp'])


def downgrade() -> None:
    # Drop tables in reverse order (handle foreign keys)
    op.drop_index('idx_smartflow_history_timestamp', table_name='smartflow_score_history')
    op.drop_index('idx_smartflow_history_ticker', table_name='smartflow_score_history')
    op.drop_table('smartflow_score_history')

    op.drop_index('idx_smartflow_logs_created', table_name='smartflow_signal_logs')
    op.drop_index('idx_smartflow_logs_ticker', table_name='smartflow_signal_logs')
    op.drop_table('smartflow_signal_logs')

    op.drop_table('smartflow_config')
