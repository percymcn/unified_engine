"""Add provisioning_jobs table for async MetaApi provisioning

Revision ID: 025_add_provisioning_jobs_table
Revises: 024_webhook_key_unique_index
Create Date: 2026-01-27

This migration adds the provisioning_jobs table to track async MetaApi
account provisioning jobs. The table stores job status, progress, and
results to support non-blocking provisioning with client polling.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '025_add_provisioning_jobs_table'
down_revision = '024_webhook_key_unique_index'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create the provisioning_jobs table for async MetaApi provisioning.
    """
    op.execute("""
        CREATE TABLE IF NOT EXISTS provisioning_jobs (
            id VARCHAR(36) PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            trading_account_id INTEGER REFERENCES trading_accounts(id),

            -- Job metadata
            platform VARCHAR(10) NOT NULL,  -- "mt4" or "mt5"
            login VARCHAR(50) NOT NULL,
            server VARCHAR(255) NOT NULL,
            account_name VARCHAR(255),

            -- Status tracking
            status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, creating, deploying, connecting, syncing, completed, failed
            status_message TEXT,
            progress_percent INTEGER DEFAULT 0,

            -- Result
            metaapi_account_id VARCHAR(100),
            error_message TEXT,

            -- Timing
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE
        );
    """)

    # Add indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_provisioning_jobs_user_id
        ON provisioning_jobs(user_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_provisioning_jobs_trading_account_id
        ON provisioning_jobs(trading_account_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_provisioning_jobs_status
        ON provisioning_jobs(status);
    """)


def downgrade():
    """
    Drop the provisioning_jobs table.
    """
    op.execute("DROP TABLE IF EXISTS provisioning_jobs CASCADE;")
