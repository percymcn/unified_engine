"""Enhance risk management tracking with trailing stop and complete execution data

Revision ID: 027_enhance_risk_tracking
Revises: 026_add_trading_session_fields
Create Date: 2026-02-01

Adds:
- trailing_stop_pips to trading_accounts for trailing stop support
- Multiple columns to execution_logs for complete trade tracking
- sl_type and tp_type to track if SL/TP are pips or price
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '027_enhance_risk_tracking'
down_revision = '026_add_trading_session_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add trailing stop support to trading_accounts
    op.add_column('trading_accounts', sa.Column('trailing_stop_pips', sa.Float(), nullable=True))
    op.add_column('trading_accounts', sa.Column('sl_type', sa.String(20), nullable=True, server_default='pips'))  # 'pips' or 'price'
    op.add_column('trading_accounts', sa.Column('tp_type', sa.String(20), nullable=True, server_default='pips'))  # 'pips' or 'price'

    # Enhance execution_logs with complete trade data
    op.add_column('execution_logs', sa.Column('stop_loss', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('take_profit', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('trailing_stop', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('entry_price', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('exit_price', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('execution_logs', sa.Column('close_reason', sa.String(50), nullable=True))  # 'stop_loss', 'take_profit', 'trailing_stop', 'manual', 'signal'
    op.add_column('execution_logs', sa.Column('pnl', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('pnl_pct', sa.Float(), nullable=True))
    op.add_column('execution_logs', sa.Column('order_id', sa.String(100), nullable=True))  # Broker order ID
    op.add_column('execution_logs', sa.Column('position_id', sa.String(100), nullable=True))  # Broker position ID

    # Enhance webhook_logs with parsed trade data
    op.add_column('webhook_logs', sa.Column('symbol', sa.String(50), nullable=True))
    op.add_column('webhook_logs', sa.Column('action', sa.String(20), nullable=True))
    op.add_column('webhook_logs', sa.Column('quantity', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('price', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('stop_loss', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('take_profit', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('signal_id', sa.String(100), nullable=True))

    # Add indexes for common queries
    op.create_index('ix_execution_logs_account_id', 'execution_logs', ['account_id'])
    op.create_index('ix_execution_logs_created_at', 'execution_logs', ['created_at'])
    op.create_index('ix_execution_logs_status', 'execution_logs', ['status'])
    op.create_index('ix_webhook_logs_created_at', 'webhook_logs', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_webhook_logs_created_at', 'webhook_logs')
    op.drop_index('ix_execution_logs_status', 'execution_logs')
    op.drop_index('ix_execution_logs_created_at', 'execution_logs')
    op.drop_index('ix_execution_logs_account_id', 'execution_logs')

    # Remove webhook_logs columns
    op.drop_column('webhook_logs', 'signal_id')
    op.drop_column('webhook_logs', 'take_profit')
    op.drop_column('webhook_logs', 'stop_loss')
    op.drop_column('webhook_logs', 'price')
    op.drop_column('webhook_logs', 'quantity')
    op.drop_column('webhook_logs', 'action')
    op.drop_column('webhook_logs', 'symbol')

    # Remove execution_logs columns
    op.drop_column('execution_logs', 'position_id')
    op.drop_column('execution_logs', 'order_id')
    op.drop_column('execution_logs', 'pnl_pct')
    op.drop_column('execution_logs', 'pnl')
    op.drop_column('execution_logs', 'close_reason')
    op.drop_column('execution_logs', 'closed_at')
    op.drop_column('execution_logs', 'exit_price')
    op.drop_column('execution_logs', 'entry_price')
    op.drop_column('execution_logs', 'trailing_stop')
    op.drop_column('execution_logs', 'take_profit')
    op.drop_column('execution_logs', 'stop_loss')

    # Remove trading_accounts columns
    op.drop_column('trading_accounts', 'tp_type')
    op.drop_column('trading_accounts', 'sl_type')
    op.drop_column('trading_accounts', 'trailing_stop_pips')
