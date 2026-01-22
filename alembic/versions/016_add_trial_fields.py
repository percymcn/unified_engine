"""add trial fields to users

Revision ID: 016
Revises: 015
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None

# Trial constants
MAX_TRIAL_TRADES = 100
MAX_TRIAL_DAYS = 3


def upgrade():
    """Add trial tracking columns to users table."""
    # Add trial tracking columns
    op.add_column('users', sa.Column('trial_trade_count', sa.Integer(), nullable=True, default=0))
    op.add_column('users', sa.Column('trial_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('trial_ended_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('trial_status', sa.String(length=20), nullable=True))

    # Set defaults for existing users based on subscription tier
    # New users and free tier users get trial_status = "pending"
    op.execute("UPDATE users SET trial_trade_count = 0 WHERE trial_trade_count IS NULL")
    op.execute("UPDATE users SET trial_status = 'pending' WHERE trial_status IS NULL AND subscription_tier = 'free'")
    # Pro users have already completed/bypassed trial
    op.execute("UPDATE users SET trial_status = 'completed' WHERE trial_status IS NULL AND subscription_tier = 'pro'")


def downgrade():
    """Remove trial tracking columns from users table."""
    op.drop_column('users', 'trial_status')
    op.drop_column('users', 'trial_ended_at')
    op.drop_column('users', 'trial_started_at')
    op.drop_column('users', 'trial_trade_count')
