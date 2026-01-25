"""Unify trading_accounts as source of truth and remove accounts table

Revision ID: 022_unify_trading_accounts
Revises: 021_add_default_stop_take_profit
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "022_unify_trading_accounts"
down_revision = "021_add_default_stop_take_profit"
branch_labels = None
depends_on = None


def upgrade():
    # Migrate legacy accounts rows into trading_accounts (preserve IDs for FKs).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='accounts') THEN
                INSERT INTO trading_accounts (
                    id,
                    user_id,
                    broker,
                    account_type,
                    account_number,
                    account_name,
                    api_key,
                    api_secret,
                    currency,
                    balance,
                    equity,
                    margin,
                    free_margin,
                    leverage,
                    is_active,
                    is_connected,
                    last_sync,
                    webhook_key,
                    extra_metadata,
                    created_at,
                    updated_at
                )
                SELECT
                    a.id,
                    a.user_id,
                    a.broker,
                    a.account_type,
                    a.account_id,
                    NULL,
                    a.api_key,
                    a.api_secret,
                    a.currency,
                    a.balance,
                    a.equity,
                    a.margin,
                    a.free_margin,
                    a.leverage,
                    a.is_active,
                    a.is_connected,
                    a.last_sync,
                    a.webhook_key,
                    json_build_object(
                        'server', a.server,
                        'login', a.login,
                        'password', a.password,
                        'broker_config', a.broker_config
                    ),
                    a.created_at,
                    a.updated_at
                FROM accounts a
                WHERE NOT EXISTS (
                    SELECT 1 FROM trading_accounts ta WHERE ta.id = a.id
                );
            END IF;
        END
        $$;
        """
    )

    # Repoint foreign keys from accounts -> trading_accounts.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='trades') THEN
                ALTER TABLE trades DROP CONSTRAINT IF EXISTS trades_account_id_fkey;
                ALTER TABLE trades
                    ADD CONSTRAINT trades_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='positions') THEN
                ALTER TABLE positions DROP CONSTRAINT IF EXISTS positions_account_id_fkey;
                ALTER TABLE positions
                    ADD CONSTRAINT positions_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='orders') THEN
                ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_account_id_fkey;
                ALTER TABLE orders
                    ADD CONSTRAINT orders_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='execution_logs') THEN
                ALTER TABLE execution_logs DROP CONSTRAINT IF EXISTS execution_logs_account_id_fkey;
                ALTER TABLE execution_logs
                    ADD CONSTRAINT execution_logs_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='alerts') THEN
                ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_account_id_fkey;
                ALTER TABLE alerts
                    ADD CONSTRAINT alerts_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='account_strategies') THEN
                ALTER TABLE account_strategies DROP CONSTRAINT IF EXISTS account_strategies_account_id_fkey;
                ALTER TABLE account_strategies
                    ADD CONSTRAINT account_strategies_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='broker_symbol_formats') THEN
                ALTER TABLE broker_symbol_formats DROP CONSTRAINT IF EXISTS broker_symbol_formats_account_id_fkey;
                ALTER TABLE broker_symbol_formats
                    ADD CONSTRAINT broker_symbol_formats_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='user_contract_positions') THEN
                ALTER TABLE user_contract_positions DROP CONSTRAINT IF EXISTS user_contract_positions_account_id_fkey;
                ALTER TABLE user_contract_positions
                    ADD CONSTRAINT user_contract_positions_account_id_fkey
                    FOREIGN KEY (account_id) REFERENCES trading_accounts(id);
            END IF;
        END
        $$;
        """
    )

    # Drop legacy accounts table after migration.
    op.execute("DROP TABLE IF EXISTS accounts;")


def downgrade():
    # Recreate legacy accounts table (minimal compatible schema).
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer()),
        sa.Column("account_id", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("broker", sa.Enum(
            "tradelocker", "topstep", "truforex", "mt4", "mt5", "tradovate", "projectx",
            name="brokertype",
            create_type=False
        ), nullable=False),
        sa.Column("account_type", sa.Enum(
            "live", "demo", "evaluation",
            name="accounttype",
            create_type=False
        ), nullable=False),
        sa.Column("currency", sa.String(), default="USD"),
        sa.Column("balance", sa.Float(), default=0.0),
        sa.Column("equity", sa.Float(), default=0.0),
        sa.Column("margin", sa.Float(), default=0.0),
        sa.Column("free_margin", sa.Float(), default=0.0),
        sa.Column("leverage", sa.Integer(), default=100),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_connected", sa.Boolean(), default=False),
        sa.Column("api_key", sa.String()),
        sa.Column("api_secret", sa.String()),
        sa.Column("server", sa.String()),
        sa.Column("login", sa.Integer()),
        sa.Column("password", sa.String()),
        sa.Column("broker_config", sa.JSON()),
        sa.Column("last_sync", sa.DateTime(timezone=True)),
        sa.Column("webhook_key", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    # Restore data from trading_accounts into accounts.
    op.execute(
        """
        INSERT INTO accounts (
            id,
            user_id,
            account_id,
            broker,
            account_type,
            currency,
            balance,
            equity,
            margin,
            free_margin,
            leverage,
            is_active,
            is_connected,
            api_key,
            api_secret,
            last_sync,
            webhook_key,
            created_at,
            updated_at,
            server,
            login,
            password,
            broker_config
        )
        SELECT
            ta.id,
            ta.user_id,
            ta.account_number,
            ta.broker,
            ta.account_type,
            ta.currency,
            ta.balance,
            ta.equity,
            ta.margin,
            ta.free_margin,
            ta.leverage,
            ta.is_active,
            ta.is_connected,
            ta.api_key,
            ta.api_secret,
            ta.last_sync,
            ta.webhook_key,
            ta.created_at,
            ta.updated_at,
            (ta.extra_metadata->>'server'),
            NULLIF(ta.extra_metadata->>'login', '')::integer,
            (ta.extra_metadata->>'password'),
            (ta.extra_metadata->'broker_config')
        FROM trading_accounts ta;
        """
    )

    # Repoint foreign keys back to accounts.
    op.execute(
        """
        DO $$
        BEGIN
            ALTER TABLE trades DROP CONSTRAINT IF EXISTS trades_account_id_fkey;
            ALTER TABLE trades
                ADD CONSTRAINT trades_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE positions DROP CONSTRAINT IF EXISTS positions_account_id_fkey;
            ALTER TABLE positions
                ADD CONSTRAINT positions_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_account_id_fkey;
            ALTER TABLE orders
                ADD CONSTRAINT orders_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE execution_logs DROP CONSTRAINT IF EXISTS execution_logs_account_id_fkey;
            ALTER TABLE execution_logs
                ADD CONSTRAINT execution_logs_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_account_id_fkey;
            ALTER TABLE alerts
                ADD CONSTRAINT alerts_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE account_strategies DROP CONSTRAINT IF EXISTS account_strategies_account_id_fkey;
            ALTER TABLE account_strategies
                ADD CONSTRAINT account_strategies_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE broker_symbol_formats DROP CONSTRAINT IF EXISTS broker_symbol_formats_account_id_fkey;
            ALTER TABLE broker_symbol_formats
                ADD CONSTRAINT broker_symbol_formats_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);

            ALTER TABLE user_contract_positions DROP CONSTRAINT IF EXISTS user_contract_positions_account_id_fkey;
            ALTER TABLE user_contract_positions
                ADD CONSTRAINT user_contract_positions_account_id_fkey
                FOREIGN KEY (account_id) REFERENCES accounts(id);
        END
        $$;
        """
    )
