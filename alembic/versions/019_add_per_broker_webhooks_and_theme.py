"""Add per-broker webhook keys and user theme preference

Revision ID: 019
Revises: 018
Create Date: 2026-01-22

Patch 1.2.1: Secure Broker Webhooks + Theme Isolation
- Add users.theme column (system/dark/light)
- Add accounts.webhook_key column (unique, nullable)

NOTE: This migration was fixed on 2026-01-23 to use 'accounts' table
(from models.py Account class) instead of 'trading_accounts' which
doesn't exist in the base schema created by models.py.
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

    # Add webhook_key column to accounts table (NOT trading_accounts)
    # The Account model in models.py uses __tablename__ = "accounts"
    op.add_column('accounts', sa.Column('webhook_key', sa.Text(), nullable=True))

    # Create unique index on webhook_key (allows NULL)
    op.create_index(
        'ix_accounts_webhook_key',
        'accounts',
        ['webhook_key'],
        unique=True,
        postgresql_where=sa.text('webhook_key IS NOT NULL')
    )


def downgrade():
    # Drop index
    op.drop_index('ix_accounts_webhook_key', table_name='accounts')

    # Drop columns
    op.drop_column('accounts', 'webhook_key')
    op.drop_column('users', 'theme')
