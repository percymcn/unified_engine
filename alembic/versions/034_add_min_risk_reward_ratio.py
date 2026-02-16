"""Add min_risk_reward_ratio for risk management

Revision ID: 034
Revises: 033
Create Date: 2026-02-16

Adds min_risk_reward_ratio to users (default) and trading_accounts tables.
This field enforces minimum risk-reward ratio for trades (e.g., 1:2 means
risk $1 to make $2). Already implemented in RiskEnforcementService but was
missing from database schema.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add min_risk_reward_ratio to trading_accounts table
    op.add_column('trading_accounts', sa.Column('min_risk_reward_ratio', sa.Float(), nullable=True))

    # Add default_min_risk_reward_ratio to users table
    op.add_column('users', sa.Column('default_min_risk_reward_ratio', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove from users
    op.drop_column('users', 'default_min_risk_reward_ratio')

    # Remove from trading_accounts
    op.drop_column('trading_accounts', 'min_risk_reward_ratio')
