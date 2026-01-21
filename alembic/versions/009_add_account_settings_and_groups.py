"""Add account settings and groups

Revision ID: 009
Revises: 008
Create Date: 2026-01-21

Adds:
- AccountGroup table for organizing accounts
- Position sizing columns to TradingAccount
- Risk limit columns to TradingAccount
- Account grouping columns to TradingAccount
- Signal routing columns to TradingAccount
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Create account_groups table first (referenced by trading_accounts)
    op.create_table(
        'account_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('color', sa.String(7), server_default='#6366f1'),
        sa.Column('icon', sa.String(50), server_default='folder'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_account_groups_user_id'),
    )
    op.create_index('ix_account_groups_id', 'account_groups', ['id'])
    op.create_index('ix_account_groups_user_id', 'account_groups', ['user_id'])

    # Add position sizing columns to trading_accounts
    op.add_column('trading_accounts',
        sa.Column('position_sizing_mode', sa.String(20), server_default='fixed'))
    op.add_column('trading_accounts',
        sa.Column('fixed_lot_size', sa.Float(), server_default='0.01'))
    op.add_column('trading_accounts',
        sa.Column('percent_of_balance', sa.Float(), server_default='1.0'))
    op.add_column('trading_accounts',
        sa.Column('percent_of_equity', sa.Float(), server_default='1.0'))
    op.add_column('trading_accounts',
        sa.Column('risk_percent_per_trade', sa.Float(), server_default='1.0'))

    # Add risk limit columns to trading_accounts
    op.add_column('trading_accounts',
        sa.Column('max_position_size', sa.Float(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('max_daily_loss', sa.Float(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('max_daily_loss_pct', sa.Float(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('max_drawdown_pct', sa.Float(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('max_open_positions', sa.Integer(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('max_daily_trades', sa.Integer(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('trade_cooldown_seconds', sa.Integer(), nullable=True))

    # Add account grouping columns to trading_accounts
    op.add_column('trading_accounts',
        sa.Column('group_id', sa.Integer(), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('group_name', sa.String(100), nullable=True))
    op.add_column('trading_accounts',
        sa.Column('group_color', sa.String(7), nullable=True))

    # Add foreign key constraint for group_id
    op.create_foreign_key(
        'fk_trading_accounts_group_id',
        'trading_accounts', 'account_groups',
        ['group_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add signal routing columns to trading_accounts
    op.add_column('trading_accounts',
        sa.Column('is_signal_enabled', sa.Boolean(), server_default='true'))
    op.add_column('trading_accounts',
        sa.Column('signal_priority', sa.Integer(), server_default='0'))


def downgrade():
    # Remove signal routing columns
    op.drop_column('trading_accounts', 'signal_priority')
    op.drop_column('trading_accounts', 'is_signal_enabled')

    # Remove foreign key and grouping columns
    op.drop_constraint('fk_trading_accounts_group_id', 'trading_accounts', type_='foreignkey')
    op.drop_column('trading_accounts', 'group_color')
    op.drop_column('trading_accounts', 'group_name')
    op.drop_column('trading_accounts', 'group_id')

    # Remove risk limit columns
    op.drop_column('trading_accounts', 'trade_cooldown_seconds')
    op.drop_column('trading_accounts', 'max_daily_trades')
    op.drop_column('trading_accounts', 'max_open_positions')
    op.drop_column('trading_accounts', 'max_drawdown_pct')
    op.drop_column('trading_accounts', 'max_daily_loss_pct')
    op.drop_column('trading_accounts', 'max_daily_loss')
    op.drop_column('trading_accounts', 'max_position_size')

    # Remove position sizing columns
    op.drop_column('trading_accounts', 'risk_percent_per_trade')
    op.drop_column('trading_accounts', 'percent_of_equity')
    op.drop_column('trading_accounts', 'percent_of_balance')
    op.drop_column('trading_accounts', 'fixed_lot_size')
    op.drop_column('trading_accounts', 'position_sizing_mode')

    # Drop account_groups table
    op.drop_index('ix_account_groups_user_id', 'account_groups')
    op.drop_index('ix_account_groups_id', 'account_groups')
    op.drop_table('account_groups')
