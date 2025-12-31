# Unified Trading Engine

## Overview

A comprehensive, production-ready trading system that integrates multiple trading platforms and brokers (MT4, MT5, Tradovate, TradeLocker, ProjectX) into a single, unified API. Provides real-time signal processing, risk management, portfolio tracking, and automated execution.

## How It Makes Money

### Revenue Model
- **Subscription Tiers**:
  - Starter: $99/month (1 broker account, basic signals)
  - Professional: $299/month (3 broker accounts, advanced signals, API access)
  - Enterprise: $999/month (unlimited accounts, custom AI, white-label, dedicated support)
- **Transaction Fees**: 0.1% per trade executed
- **Signal Marketplace**: Sell trading signals (30% commission)
- **API Access**: Premium API access for algo traders ($0.01 per API call)

### Target Market
- Retail traders
- Algorithmic trading firms
- Signal providers
- Trading educators
- Prop trading firms

## User Onboarding

1. **Sign Up**: Create account via frontend
2. **Broker Connection**: Connect MT4, MT5, Tradovate, TradeLocker, or ProjectX accounts
3. **Risk Setup**: Configure risk parameters and position sizing
4. **Signal Source**: Connect signal providers or use built-in AI signals
5. **Payment Setup**: Configure Stripe for subscription
6. **Trial Period**: 7-day free trial with demo account
7. **Subscription**: Choose plan and activate

## API Endpoints

### Base URL
```
http://localhost:8015
```

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/me` - Get current user

### Accounts
- `GET /accounts` - List all accounts
- `GET /accounts/{id}` - Get account details
- `POST /accounts` - Create new account
- `PUT /accounts/{id}` - Update account

### Signals
- `GET /signals` - List signals
- `POST /signals` - Create signal
- `POST /signals/{id}/execute` - Execute signal
- `GET /signals/{id}` - Get signal details

### Trades
- `GET /trades` - List trades
- `GET /trades/{id}` - Get trade details
- `POST /trades/{id}/close` - Close trade
- `GET /trades/positions` - Get open positions

### Positions
- `GET /positions` - List open positions
- `GET /positions/{id}` - Get position details
- `POST /positions/{id}/close` - Close position

### Webhooks
- `POST /webhooks/signal` - Receive webhook signals
- `POST /webhooks/trade` - Receive webhook trades

### Health
- `GET /health` - Health check
- `GET /healthz` - Standard health check

## UI Routes

- `/` - Landing page
- `/login` - User login
- `/signup` - User registration
- `/dashboard` - Trading dashboard
- `/brokers` - Broker management
- `/signals` - Signal management
- `/trades` - Trade history
- `/positions` - Open positions
- `/portfolio` - Portfolio view
- `/analytics` - Performance analytics
- `/settings` - Account settings
- `/billing` - Subscription and billing

## NATS Events

### Subjects
- `empire.trading.user.created` - New user registered
- `empire.trading.broker.connected` - Broker account connected
- `empire.trading.signal.received` - New signal received
- `empire.trading.signal.executed` - Signal executed
- `empire.trading.trade.executed` - Trade executed
- `empire.trading.trade.closed` - Trade closed
- `empire.trading.position.opened` - Position opened
- `empire.trading.position.closed` - Position closed
- `empire.trading.portfolio.updated` - Portfolio updated
- `empire.trading.subscription.updated` - Subscription changed

### Event Format
```json
{
  "event": "trade.executed",
  "trade_id": "uuid",
  "user_id": "uuid",
  "broker": "mt5",
  "symbol": "EURUSD",
  "timestamp": "2025-12-08T00:00:00Z",
  "data": {}
}
```

## N8N Workflows

Location: `/n8n/`

### Planned Workflows
1. **Signal Processing Pipeline** - Process incoming signals
2. **Trade Execution Automation** - Automated trade execution
3. **Risk Management Alerts** - Risk limit monitoring
4. **Portfolio Rebalancing** - Automatic portfolio rebalancing
5. **Performance Reporting** - Daily/weekly performance reports
6. **Subscription Management** - Handle renewals and payments

## MCP Connectors

Location: `/mcp/connector.json`

### Planned MCP Tools
- `execute_trade` - Execute a trade
- `get_positions` - Get open positions
- `get_portfolio` - Get portfolio data
- `connect_broker` - Connect broker account
- `get_signals` - Get trading signals
- `get_performance` - Get performance metrics

## Pricing

### Starter Plan - $99/month
- 1 broker account
- Basic signal processing
- Email support
- Basic analytics

### Professional Plan - $299/month
- 3 broker accounts
- Advanced signal processing
- API access (1,000 calls/month)
- Priority support
- Advanced analytics
- Custom workflows (3)

### Enterprise Plan - $999/month
- Unlimited broker accounts
- Custom AI signal processing
- Unlimited API access
- Dedicated support manager
- Full analytics suite
- Unlimited custom workflows
- White-label options
- SLA guarantee

## Deployment

### Docker Compose
```bash
cd deploy
docker-compose up -d
```

### Environment Variables
See `.env.example` in root directory

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `NATS_URL` - NATS server URL
- `JWT_SECRET` - Secret for JWT tokens
- `STRIPE_SECRET_KEY` - Stripe API key
- Broker API keys (MT4, MT5, Tradovate, TradeLocker, ProjectX)

## Status

- **Backend**: ✅ Complete (FastAPI with multi-broker support)
- **Frontend**: ✅ Complete (React/Vite UI)
- **N8N Workflows**: ❌ Missing
- **MCP Connector**: ❌ Missing
- **Onboarding Flow**: ⚠️ Partial
- **Revenue Integration**: ⚠️ Partial (Stripe stubs exist)

## Next Steps

1. Create N8N workflows for automation
2. Build MCP connector
3. Complete onboarding flow
4. Add Stripe payment integration
5. Connect to master dashboard
