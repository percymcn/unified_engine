"""Add unique index for webhook_key on trading_accounts

Revision ID: 024_add_unique_index_trading_accounts_webhook_key
Revises: 023_fix_fk_to_trading_accounts
Create Date: 2026-01-24

This migration adds a partial unique index on the webhook_key column
of the trading_accounts table. The index only applies to non-NULL values,
ensuring webhook keys are unique when present while allowing multiple
NULL values (accounts without custom webhooks).
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '024_webhook_key_unique_index'
down_revision = '023_fix_fk_to_trading_accounts'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add unique partial index on webhook_key for trading_accounts.
    Uses CREATE INDEX IF NOT EXISTS for idempotency.
    """
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_trading_accounts_webhook_key
        ON trading_accounts(webhook_key)
        WHERE webhook_key IS NOT NULL;
    """)


def downgrade():
    """
    Remove the unique partial index on webhook_key.
    Uses DROP INDEX IF EXISTS for idempotency.
    """
    op.execute("""
        DROP INDEX IF EXISTS ix_trading_accounts_webhook_key;
    """)
