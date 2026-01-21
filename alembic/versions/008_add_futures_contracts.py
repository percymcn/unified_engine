"""add futures_contracts and user_contract_positions tables

Revision ID: 008_add_futures_contracts
Revises: 007_add_broker_symbol_format
Create Date: 2026-01-21 23:24:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_futures_contracts'
down_revision = '007_add_broker_symbol_format'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create futures_contracts table
    op.create_table(
        'futures_contracts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('symbol_root', sa.String(10), nullable=False),
        sa.Column('contract_code', sa.String(20), nullable=False, unique=True),
        sa.Column('month_code', sa.String(1), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_trading_day', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rollover_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('next_contract', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes for futures_contracts
    op.create_index('ix_futures_contracts_symbol_root', 'futures_contracts', ['symbol_root'])
    op.create_index('ix_futures_contracts_contract_code', 'futures_contracts', ['contract_code'])

    # Create user_contract_positions table
    op.create_table(
        'user_contract_positions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('contract_code', sa.String(20), nullable=False),
        sa.Column('symbol_root', sa.String(10), nullable=False),
        sa.Column('last_traded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes for user_contract_positions
    op.create_index('ix_user_contract_positions_user_id', 'user_contract_positions', ['user_id'])
    op.create_index('ix_user_contract_positions_account_id', 'user_contract_positions', ['account_id'])
    op.create_index('ix_user_contract_positions_contract_code', 'user_contract_positions', ['contract_code'])

    # Create unique constraint for user/account/contract combination
    op.create_unique_constraint(
        'uq_user_account_contract',
        'user_contract_positions',
        ['user_id', 'account_id', 'contract_code']
    )


def downgrade() -> None:
    # Drop user_contract_positions
    op.drop_constraint('uq_user_account_contract', 'user_contract_positions', type_='unique')
    op.drop_index('ix_user_contract_positions_contract_code', table_name='user_contract_positions')
    op.drop_index('ix_user_contract_positions_account_id', table_name='user_contract_positions')
    op.drop_index('ix_user_contract_positions_user_id', table_name='user_contract_positions')
    op.drop_table('user_contract_positions')

    # Drop futures_contracts
    op.drop_index('ix_futures_contracts_contract_code', table_name='futures_contracts')
    op.drop_index('ix_futures_contracts_symbol_root', table_name='futures_contracts')
    op.drop_table('futures_contracts')
