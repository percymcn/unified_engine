"""Add token_expires_at and oauth_environment to trading_accounts

Revision ID: 005_add_token_expiry
Revises: 004_add_subscription_fields
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '005_add_token_expiry'
down_revision = '004_add_subscription_fields'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add OAuth token management columns to trading_accounts.

    Idempotent: Only adds columns if the table exists and columns don't exist.
    If trading_accounts doesn't exist, SQLAlchemy will create it with the columns
    on app startup via Base.metadata.create_all().
    """
    if not table_exists('trading_accounts'):
        # Table doesn't exist yet - it will be created by SQLAlchemy
        # with the new columns already defined in the model
        return

    if not column_exists('trading_accounts', 'token_expires_at'):
        op.add_column(
            'trading_accounts',
            sa.Column('token_expires_at', sa.DateTime(), nullable=True)
        )

    if not column_exists('trading_accounts', 'oauth_environment'):
        op.add_column(
            'trading_accounts',
            sa.Column('oauth_environment', sa.String(10), nullable=True)
        )


def downgrade() -> None:
    """Remove OAuth token management columns from trading_accounts."""
    if not table_exists('trading_accounts'):
        return

    if column_exists('trading_accounts', 'token_expires_at'):
        op.drop_column('trading_accounts', 'token_expires_at')

    if column_exists('trading_accounts', 'oauth_environment'):
        op.drop_column('trading_accounts', 'oauth_environment')
