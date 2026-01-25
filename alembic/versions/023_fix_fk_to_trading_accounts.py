"""Fix FK references from accounts to trading_accounts

Revision ID: 023_fix_fk_to_trading_accounts
Revises: 022_unify_trading_accounts
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '023_fix_fk_to_trading_accounts'
down_revision = '022_unify_trading_accounts'
branch_labels = None
depends_on = None


def upgrade():
    """
    Update all foreign key references from legacy 'accounts' table
    to canonical 'trading_accounts' table, then drop legacy table.
    """
    # Tables that have FK to accounts (need to point to trading_accounts instead)
    tables_with_account_fk = [
        ('trades', 'account_id', 'trades_account_id_fkey'),
        ('positions', 'account_id', 'positions_account_id_fkey'),
        ('orders', 'account_id', 'orders_account_id_fkey'),
        ('execution_logs', 'account_id', 'execution_logs_account_id_fkey'),
        ('alerts', 'account_id', 'alerts_account_id_fkey'),
        ('account_strategies', 'account_id', 'account_strategies_account_id_fkey'),
        ('broker_symbol_formats', 'account_id', 'broker_symbol_formats_account_id_fkey'),
        ('user_contract_positions', 'account_id', 'user_contract_positions_account_id_fkey'),
    ]

    for table_name, column_name, constraint_name in tables_with_account_fk:
        # Drop old FK constraint (if exists)
        try:
            op.drop_constraint(constraint_name, table_name, type_='foreignkey')
        except Exception:
            # Constraint might not exist or have different name
            pass

        # Create new FK to trading_accounts
        op.create_foreign_key(
            f'{table_name}_{column_name}_fkey',
            table_name,
            'trading_accounts',
            [column_name],
            ['id'],
            ondelete='SET NULL'
        )

    # Drop the legacy accounts table (it has 0 rows)
    op.drop_table('accounts')


def downgrade():
    """
    Recreate legacy accounts table and restore FK references.
    Note: Data will be lost - this is a one-way migration for production.
    """
    # Recreate legacy accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('account_id', sa.String(), nullable=True),
        sa.Column('broker', sa.String(11), nullable=True),
        sa.Column('account_type', sa.String(10), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('balance', sa.Float(), nullable=True),
        sa.Column('equity', sa.Float(), nullable=True),
        sa.Column('margin', sa.Float(), nullable=True),
        sa.Column('free_margin', sa.Float(), nullable=True),
        sa.Column('leverage', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_connected', sa.Boolean(), default=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('api_secret', sa.String(), nullable=True),
        sa.Column('server', sa.String(), nullable=True),
        sa.Column('login', sa.Integer(), nullable=True),
        sa.Column('password', sa.String(), nullable=True),
        sa.Column('broker_config', sa.JSON(), nullable=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('webhook_key', sa.Text(), nullable=True),
    )

    # Restore FK to accounts
    tables_with_account_fk = [
        ('trades', 'account_id'),
        ('positions', 'account_id'),
        ('orders', 'account_id'),
        ('execution_logs', 'account_id'),
        ('alerts', 'account_id'),
        ('account_strategies', 'account_id'),
        ('broker_symbol_formats', 'account_id'),
        ('user_contract_positions', 'account_id'),
    ]

    for table_name, column_name in tables_with_account_fk:
        # Drop FK to trading_accounts
        try:
            op.drop_constraint(f'{table_name}_{column_name}_fkey', table_name, type_='foreignkey')
        except Exception:
            pass

        # Create FK to accounts
        op.create_foreign_key(
            f'{table_name}_{column_name}_fkey',
            table_name,
            'accounts',
            [column_name],
            ['id'],
            ondelete='SET NULL'
        )
