"""Add daily_pnl and account_equity_history tables

Revision ID: 012_add_daily_pnl
Revises: 011_add_rejected_signals
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012_add_daily_pnl'
down_revision = '011_add_rejected_signals'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create daily_pnl and account_equity_history tables"""
    # Create daily_pnl table
    op.create_table(
        'daily_pnl',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('account_id', sa.Integer, sa.ForeignKey('trading_accounts.id'), nullable=False, index=True),
        sa.Column('date', sa.Date, nullable=False, index=True),

        # P&L tracking
        sa.Column('starting_balance', sa.Float, nullable=False),
        sa.Column('current_balance', sa.Float),
        sa.Column('realized_pnl', sa.Float, server_default='0.0'),
        sa.Column('unrealized_pnl', sa.Float, server_default='0.0'),
        sa.Column('total_pnl', sa.Float, server_default='0.0'),
        sa.Column('pnl_percent', sa.Float, server_default='0.0'),

        # Trade stats
        sa.Column('trades_count', sa.Integer, server_default='0'),
        sa.Column('winning_trades', sa.Integer, server_default='0'),
        sa.Column('losing_trades', sa.Integer, server_default='0'),

        # Status
        sa.Column('is_trading_halted', sa.Boolean, server_default='false'),
        sa.Column('halt_reason', sa.String(100)),
        sa.Column('halted_at', sa.DateTime),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create unique composite index for account_id + date
    op.create_index(
        'ix_daily_pnl_account_date',
        'daily_pnl',
        ['account_id', 'date'],
        unique=True
    )

    # Create account_equity_history table
    op.create_table(
        'account_equity_history',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('account_id', sa.Integer, sa.ForeignKey('trading_accounts.id'), nullable=False, index=True),

        # Equity snapshot
        sa.Column('equity', sa.Float, nullable=False),
        sa.Column('balance', sa.Float, nullable=False),
        sa.Column('peak_equity', sa.Float, nullable=False),
        sa.Column('drawdown', sa.Float, server_default='0.0'),
        sa.Column('drawdown_pct', sa.Float, server_default='0.0'),

        # Timestamp
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    """Remove daily_pnl and account_equity_history tables"""
    # Drop daily_pnl index first
    op.drop_index('ix_daily_pnl_account_date', table_name='daily_pnl')

    # Drop tables
    op.drop_table('daily_pnl')
    op.drop_table('account_equity_history')
