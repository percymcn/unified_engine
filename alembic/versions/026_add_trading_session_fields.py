"""Add trading session fields to momentum_settings

Revision ID: 026_add_trading_session_fields
Revises: 025
Create Date: 2026-02-01

Adds fields for controlling when webhooks are active:
- trading_session_enabled: Toggle to enable/disable session restriction
- trading_session_start: Start time (HH:MM format)
- trading_session_end: End time (HH:MM format)
- trading_session_timezone: IANA timezone string
- trading_session_days: JSON array of active days (1=Mon, 7=Sun)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '026_add_trading_session_fields'
down_revision = '025_add_provisioning_jobs_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add trading session columns to momentum_settings table
    op.add_column('momentum_settings', sa.Column('trading_session_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('momentum_settings', sa.Column('trading_session_start', sa.String(5), nullable=True, server_default='09:30'))
    op.add_column('momentum_settings', sa.Column('trading_session_end', sa.String(5), nullable=True, server_default='16:00'))
    op.add_column('momentum_settings', sa.Column('trading_session_timezone', sa.String(50), nullable=True, server_default='America/New_York'))
    op.add_column('momentum_settings', sa.Column('trading_session_days', sa.JSON(), nullable=True, server_default='[1, 2, 3, 4, 5]'))


def downgrade():
    # Remove trading session columns
    op.drop_column('momentum_settings', 'trading_session_days')
    op.drop_column('momentum_settings', 'trading_session_timezone')
    op.drop_column('momentum_settings', 'trading_session_end')
    op.drop_column('momentum_settings', 'trading_session_start')
    op.drop_column('momentum_settings', 'trading_session_enabled')
