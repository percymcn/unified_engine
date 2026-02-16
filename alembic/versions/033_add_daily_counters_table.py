"""Add daily_counters table for persistent trade counting

Revision ID: 033
Revises: 032
Create Date: 2026-02-16

Adds daily_counters table to persist trade counts and timestamps across
container restarts. Required for max_daily_trades enforcement.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create daily_counters table for persistent trade tracking
    op.create_table(
        'daily_counters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('trading_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('signals_received', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trades_executed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trades_rejected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_trade_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Composite unique constraint for account_id + date
        sa.UniqueConstraint('account_id', 'date', name='uq_daily_counters_account_date')
    )

    # Create indexes for common queries
    op.create_index('ix_daily_counters_account_id', 'daily_counters', ['account_id'])
    op.create_index('ix_daily_counters_date', 'daily_counters', ['date'])
    op.create_index('ix_daily_counters_account_date', 'daily_counters', ['account_id', 'date'])


def downgrade() -> None:
    op.drop_index('ix_daily_counters_account_date', 'daily_counters')
    op.drop_index('ix_daily_counters_date', 'daily_counters')
    op.drop_index('ix_daily_counters_account_id', 'daily_counters')
    op.drop_table('daily_counters')
