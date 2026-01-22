# Domain Model: Unified Trading Engine

## Key Domain Entities

### Core Trading Entities

| Entity | Location | Purpose |
|--------|----------|---------|
| User | `app/models/models.py` | User account, authentication |
| TradingAccount | `app/models/database_models.py` | Broker account connection |
| Signal | `app/models/models.py` | Incoming trading signal |
| Trade | `app/models/models.py` | Executed trade record |
| Position | `app/models/models.py` | Open position |
| Order | `app/models/models.py` | Pending order |
| Credential | `app/models/database_models.py` | Encrypted broker credentials |
| WebhookConfig | `app/models/database_models.py` | Webhook routing configuration |

### Domain Layer Entities

Location: `app/domain/entities/`

| Entity | File | Purpose |
|--------|------|---------|
| Order | `order.py` | Domain order with value objects |
| Position | `position.py` | Domain position |
| Trade | `trade.py` | Domain trade |

### Enums

Location: `app/models/database_models.py`

```python
class BrokerType(enum.Enum):
    TRADELOCKER = "tradelocker"
    TRADOVATE = "tradovate"
    PROJECTX = "projectx"
    TOPSTEP = "topstep"
    TRUFOREX = "truforex"
    MT4 = "mt4"
    MT5 = "mt5"

class AccountType(enum.Enum):
    LIVE = "live"
    DEMO = "demo"
    FUNDED = "funded"
    EVALUATION = "evaluation"

class OrderStatus(enum.Enum):
    PENDING, OPEN, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED, EXPIRED

class SignalStatus(enum.Enum):
    RECEIVED, PROCESSING, EXECUTED, FAILED, IGNORED

class RejectedSignalReason(enum.Enum):
    DAILY_LIMIT, CONCURRENT_LIMIT, SYMBOL_LIMIT, COOLDOWN,
    DAILY_LOSS, DRAWDOWN, RISK_REWARD, DISABLED, DUPLICATE_ENTRY, TRIAL_EXPIRED
```

## Database Tables (PostgreSQL)

### User Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_status VARCHAR(20) DEFAULT 'active',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### TradingAccount Table
```sql
CREATE TABLE trading_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    broker broker_type_enum NOT NULL,
    account_type account_type_enum NOT NULL,
    account_number VARCHAR(100) NOT NULL,
    account_name VARCHAR(255),

    -- Encrypted credentials
    api_key VARCHAR(500),
    api_secret VARCHAR(500),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    oauth_environment VARCHAR(10),

    -- Account info
    currency VARCHAR(10) DEFAULT 'USD',
    leverage FLOAT DEFAULT 1.0,
    balance FLOAT DEFAULT 0.0,
    equity FLOAT DEFAULT 0.0,
    margin FLOAT DEFAULT 0.0,
    free_margin FLOAT DEFAULT 0.0,

    -- Position sizing
    position_sizing_mode VARCHAR(20) DEFAULT 'fixed',
    fixed_lot_size FLOAT DEFAULT 0.01,
    percent_of_balance FLOAT DEFAULT 1.0,
    risk_percent_per_trade FLOAT DEFAULT 1.0,

    -- Risk limits
    max_position_size FLOAT,
    max_daily_loss FLOAT,
    max_daily_loss_pct FLOAT,
    max_drawdown_pct FLOAT,
    max_open_positions INTEGER,
    max_daily_trades INTEGER,
    trade_cooldown_seconds INTEGER,
    max_positions_per_symbol INTEGER DEFAULT 1,

    -- Grouping
    group_id INTEGER REFERENCES account_groups(id),
    group_name VARCHAR(100),

    -- Routing
    is_signal_enabled BOOLEAN DEFAULT TRUE,
    signal_priority INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_connected BOOLEAN DEFAULT FALSE,
    last_sync TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Credential Table
```sql
CREATE TABLE credentials (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id INTEGER REFERENCES users(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,      -- api_key, password, certificate, token, oauth
    service VARCHAR(50) NOT NULL,   -- mt4, mt5, tradelocker, tradovate, projectx
    encrypted_data TEXT NOT NULL,   -- Fernet encrypted JSON
    description TEXT,

    expires_at TIMESTAMP,
    rotation_days INTEGER DEFAULT 90,
    last_rotated TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### WebhookConfig Table
```sql
CREATE TABLE webhook_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    webhook_key VARCHAR(255) UNIQUE NOT NULL,
    source VARCHAR(100) NOT NULL,  -- tradingview, trailhacker, custom

    -- Routing
    routing_strategy VARCHAR(30) DEFAULT 'default_only',
    default_account_id INTEGER REFERENCES trading_accounts(id),
    specific_account_ids JSON,
    routing_rules JSON,

    -- Filters
    symbol_filter JSON,
    action_filter JSON,

    is_active BOOLEAN DEFAULT TRUE,

    -- Stats
    total_signals INTEGER DEFAULT 0,
    successful_signals INTEGER DEFAULT 0,
    failed_signals INTEGER DEFAULT 0,
    last_signal_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Other Tables

| Table | Purpose |
|-------|---------|
| signals | Received signals log |
| trades | Executed trade records |
| positions | Open position tracking |
| orders | Pending order tracking |
| webhook_logs | Signal processing logs |
| account_groups | Account organization |
| rejected_signals | Risk rejection log |
| daily_pnl | Daily P&L tracking |
| account_equity_history | Drawdown tracking |
| performance_metrics | Period performance |
| audit_logs | User action audit |
| api_keys | User API key management |
| symbol_aliases | Symbol mapping rules |
| futures_contracts | Contract specifications |

## Migrations

Location: `alembic/versions/`

| Migration | Purpose |
|-----------|---------|
| 002_add_strategy_support | Strategy model support |
| 003_add_credentials_table | Credential storage |
| 004_add_subscription_fields | Billing support |
| 005_add_token_expiry | OAuth token tracking |
| 006_add_symbol_alias | Symbol mapping |
| 007_add_broker_symbol_format | Broker-specific symbols |
| 008_add_futures_contracts | Futures support |
| 009_add_account_settings_and_groups | Account grouping |
| 010_add_routing_strategy | Signal routing rules |
| 011_add_rejected_signals | Risk rejection log |
| 012_add_daily_pnl | P&L tracking |
| 013_add_user_risk_settings | Global risk limits |
| 014_add_user_preferences | UI preferences |
| 015_add_avatar_url | Profile images |
| 016_add_trial_fields | Free trial support |
| 017_add_deduplication_settings | Duplicate signal handling |

---
*Generated: 2026-01-22*
