"""Add per-broker webhook keys and user theme preference

Revision ID: 019
Revises: 018
Create Date: 2026-01-22

Patch 1.2.1: Secure Broker Webhooks + Theme Isolation
- Add users.theme column (system/dark/light)
- Add trading_accounts.webhook_key column (unique, nullable)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    # Add theme column to users table
    op.add_column('users', sa.Column('theme', sa.String(10), nullable=False, server_default='system'))
    
    # Add webhook_key column to trading_accounts table
    op.add_column('trading_accounts', sa.Column('webhook_key', sa.Text(), nullable=True))
    
    # Create unique index on webhook_key (allows NULL)
    op.create_index(
        'ix_trading_accounts_webhook_key',
        'trading_accounts',
        ['webhook_key'],
        unique=True,
        postgresql_where=sa.text('webhook_key IS NOT NULL')
    )


def downgrade():
    # Drop index
    op.drop_index('ix_trading_accounts_webhook_key', table_name='trading_accounts')
    
    # Drop columns
    op.drop_column('trading_accounts', 'webhook_key')
    op.drop_column('users', 'theme')
