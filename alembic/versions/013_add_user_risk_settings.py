"""add user risk settings

Revision ID: 013
Revises: 012
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    """Add global risk settings columns to users table."""
    # Add global risk limit columns
    op.add_column('users', sa.Column('default_max_daily_trades', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('default_max_open_positions', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('default_max_daily_loss', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('default_max_daily_loss_pct', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('default_max_drawdown_pct', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('default_trade_cooldown_seconds', sa.Integer(), nullable=True))

    # Add global position sizing defaults
    op.add_column('users', sa.Column('default_position_sizing_mode', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('default_fixed_lot_size', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('default_risk_percent_per_trade', sa.Float(), nullable=True))

    # Add global risk enforcement toggle
    op.add_column('users', sa.Column('risk_management_enabled', sa.Boolean(), nullable=True))

    # Set defaults for existing users
    op.execute("UPDATE users SET default_position_sizing_mode = 'fixed' WHERE default_position_sizing_mode IS NULL")
    op.execute("UPDATE users SET default_fixed_lot_size = 0.01 WHERE default_fixed_lot_size IS NULL")
    op.execute("UPDATE users SET default_risk_percent_per_trade = 1.0 WHERE default_risk_percent_per_trade IS NULL")
    op.execute("UPDATE users SET risk_management_enabled = true WHERE risk_management_enabled IS NULL")


def downgrade():
    """Remove user risk settings columns."""
    op.drop_column('users', 'risk_management_enabled')
    op.drop_column('users', 'default_risk_percent_per_trade')
    op.drop_column('users', 'default_fixed_lot_size')
    op.drop_column('users', 'default_position_sizing_mode')
    op.drop_column('users', 'default_trade_cooldown_seconds')
    op.drop_column('users', 'default_max_drawdown_pct')
    op.drop_column('users', 'default_max_daily_loss_pct')
    op.drop_column('users', 'default_max_daily_loss')
    op.drop_column('users', 'default_max_open_positions')
    op.drop_column('users', 'default_max_daily_trades')
