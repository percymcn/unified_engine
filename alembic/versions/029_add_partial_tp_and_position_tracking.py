"""Add partial TP configuration and position tracking

Revision ID: 029
Revises: 028
Create Date: 2026-02-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '029_partial_tp'
down_revision = '028_auto_confirm'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add partial TP and platform-managed SL/TP settings to trading_accounts
    op.add_column('trading_accounts', sa.Column('partial_tp_enabled', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('trading_accounts', sa.Column('partial_tp_config', JSON, nullable=True))
    op.add_column('trading_accounts', sa.Column('platform_managed_sl_tp', sa.Boolean(), server_default='false', nullable=True))

    # Create position_trades table for tracking open positions with partial TP
    op.create_table(
        'position_trades',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('trading_accounts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('broker_position_id', sa.String(100), nullable=True, index=True),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),  # 'buy' or 'sell'
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('initial_volume', sa.Float(), nullable=False),
        sa.Column('current_volume', sa.Float(), nullable=False),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('take_profit', sa.Float(), nullable=True),  # Final TP
        sa.Column('partial_tp_levels', JSON, nullable=True),  # Array of TP levels with close %
        sa.Column('executed_tp_levels', JSON, server_default='[]', nullable=True),  # Executed TP indices
        sa.Column('trailing_stop_distance', sa.Float(), nullable=True),
        sa.Column('current_trailing_sl', sa.Float(), nullable=True),  # Current trailing SL price
        sa.Column('status', sa.String(20), server_default='open', nullable=False, index=True),  # open, partial, closed
        sa.Column('webhook_id', sa.String(100), nullable=True),
        sa.Column('signal_id', sa.String(100), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
    )

    # Create index for efficient position lookups
    op.create_index('ix_position_trades_account_status', 'position_trades', ['account_id', 'status'])
    op.create_index('ix_position_trades_symbol', 'position_trades', ['symbol'])


def downgrade() -> None:
    op.drop_index('ix_position_trades_symbol', 'position_trades')
    op.drop_index('ix_position_trades_account_status', 'position_trades')
    op.drop_table('position_trades')
    op.drop_column('trading_accounts', 'platform_managed_sl_tp')
    op.drop_column('trading_accounts', 'partial_tp_config')
    op.drop_column('trading_accounts', 'partial_tp_enabled')
