"""Add webhook_configs table for signal routing

Revision ID: 048_add_webhook_configs
Revises: 047_add_portfolio_risk_snapshots
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '048_add_webhook_configs'
down_revision = '047_portfolio_risk'
branch_labels = None
depends_on = None


def upgrade():
    """Create webhook_configs table for multi-account signal routing"""
    op.create_table(
        'webhook_configs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), nullable=False),  # No FK - users table may not exist in all deployments

        # Config
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('webhook_key', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('source', sa.String(100), nullable=False),  # tradingview, trailhacker, smartflow, custom

        # Routing Configuration
        sa.Column('routing_strategy', sa.String(30), server_default='default_only'),
        sa.Column('default_account_id', sa.Integer(), nullable=True),  # No FK - trading_accounts may not exist
        sa.Column('specific_account_ids', postgresql.JSON(), nullable=True),  # List of account IDs
        sa.Column('routing_rules', postgresql.JSON(), nullable=True),  # Complex routing logic

        # Filters
        sa.Column('symbol_filter', postgresql.JSON(), nullable=True),  # Symbols whitelist
        sa.Column('action_filter', postgresql.JSON(), nullable=True),  # Actions whitelist

        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true'),

        # Stats
        sa.Column('total_signals', sa.Integer(), server_default='0'),
        sa.Column('successful_signals', sa.Integer(), server_default='0'),
        sa.Column('failed_signals', sa.Integer(), server_default='0'),
        sa.Column('last_signal_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for common queries
    op.create_index('ix_webhook_configs_user_id', 'webhook_configs', ['user_id'])
    op.create_index('ix_webhook_configs_is_active', 'webhook_configs', ['is_active'])


def downgrade():
    """Drop webhook_configs table"""
    op.drop_index('ix_webhook_configs_is_active', table_name='webhook_configs')
    op.drop_index('ix_webhook_configs_user_id', table_name='webhook_configs')
    op.drop_table('webhook_configs')
