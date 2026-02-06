"""Add max_daily_profit fields for profit target risk management

Revision ID: 032
Revises: 031
Create Date: 2025-02-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '032'
down_revision = '031'  # References 031_add_webhook_log_extracted_fields.py
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add max_daily_profit to trading_accounts table
    op.add_column('trading_accounts', sa.Column('max_daily_profit', sa.Float(), nullable=True))
    op.add_column('trading_accounts', sa.Column('max_daily_profit_pct', sa.Float(), nullable=True))

    # Add default_max_daily_profit to users table
    op.add_column('users', sa.Column('default_max_daily_profit', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('default_max_daily_profit_pct', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove from users
    op.drop_column('users', 'default_max_daily_profit_pct')
    op.drop_column('users', 'default_max_daily_profit')

    # Remove from trading_accounts
    op.drop_column('trading_accounts', 'max_daily_profit_pct')
    op.drop_column('trading_accounts', 'max_daily_profit')
