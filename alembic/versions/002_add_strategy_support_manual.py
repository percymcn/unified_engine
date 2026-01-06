"""Create API Keys, Strategies, and Account Strategies tables - Manual SQL

Revision ID: 002_add_strategy_support_manual
Revises:
Create Date: 2026-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_strategy_support_manual'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create api_keys table
    op.execute("""
        CREATE TABLE api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            key_hash VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            permissions JSON,
            is_active BOOLEAN DEFAULT TRUE,
            expires_at TIMESTAMP WITH TIME ZONE,
            last_used_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE UNIQUE INDEX ix_api_keys_key_hash ON api_keys(key_hash)")

    # Create strategies table
    op.execute("""
        CREATE TABLE strategies (
            id SERIAL PRIMARY KEY,
            strategy_id VARCHAR NOT NULL UNIQUE,
            strategy_name VARCHAR NOT NULL,
            strategy_version VARCHAR NOT NULL,
            strategy_source VARCHAR NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            parameters JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE UNIQUE INDEX ix_strategies_strategy_id ON strategies(strategy_id)")

    # Create account_strategies table
    op.execute("""
        CREATE TABLE account_strategies (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            strategy_id INTEGER NOT NULL REFERENCES strategies(id),
            is_enabled BOOLEAN DEFAULT FALSE,
            parameters JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    # Add strategy fields to signals table
    op.execute("ALTER TABLE signals ADD COLUMN strategy_id VARCHAR")
    op.execute("ALTER TABLE signals ADD COLUMN strategy_version VARCHAR")
    op.execute("ALTER TABLE signals ADD COLUMN strategy_name VARCHAR")
    op.execute("ALTER TABLE signals ADD COLUMN strategy_source VARCHAR")
    op.execute("CREATE INDEX ix_signals_strategy_id ON signals(strategy_id)")


def downgrade():
    # Remove strategy fields from signals table
    op.execute("DROP INDEX IF EXISTS ix_signals_strategy_id")
    op.execute("ALTER TABLE signals DROP COLUMN IF EXISTS strategy_source")
    op.execute("ALTER TABLE signals DROP COLUMN IF EXISTS strategy_name")
    op.execute("ALTER TABLE signals DROP COLUMN IF EXISTS strategy_version")
    op.execute("ALTER TABLE signals DROP COLUMN IF EXISTS strategy_id")

    # Drop account_strategies table
    op.execute("DROP TABLE IF EXISTS account_strategies CASCADE")

    # Drop strategies table
    op.execute("DROP INDEX IF EXISTS ix_strategies_strategy_id")
    op.execute("DROP TABLE IF EXISTS strategies CASCADE")

    # Drop api_keys table
    op.execute("DROP INDEX IF EXISTS ix_api_keys_key_hash")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
