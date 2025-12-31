# TradeLocker API Documentation

## Official Sources
- Brand API Docs: https://brand-docs.tradelocker.com/
- Socket API Docs: https://api.tradelocker.com/brand-api/socket/docs/
- Python Library: https://github.com/TradeLocker/tradelocker-python
- REST API: https://tradelocker.com/api/

## WebSocket API (BrandSocket)

### Connection Details
- Production: `wss://api.tradelocker.com/brand-api/socket.io/?type=LIVE`
- Development: `wss://api-dev.tradelocker.com/brand-api/socket.io/?type=LIVE`
- Namespace: `/brand-socket`
- Transport: `websocket`
- Query parameters: `type=LIVE` or `type=DEMO`

### Authentication
- Header: `brand-api-key: <your-api-key>`

### Events

#### Receive Events
- `stream` - All account and position updates
- `subscriptions` - Instrument quote subscriptions
- `connection` - Connection status and errors

#### Message Types (via stream event)
- `AccountStatus` - Real-time balance, equity, margin data
- `Property (SyncEnd)` - Initial sync completion signal
- `Position` - Position open/modify updates
- `ClosePosition` - Position closure details
- `OpenOrder` - Order updates

#### Quote Subscriptions (subscriptions event)
- Subscribe/unsubscribe to instrument price feeds
- Receive `Quote` messages with bid/ask prices

## Brand API Features

### Account Management
- Automated provisioning for prop, demo, and live accounts
- One-click login integration from CMS
- Account status monitoring

### Transaction Management
- Deposits and withdrawals
- Transaction history

### Trading Operations
- Order management
- Position tracking
- Risk management tools

### Reporting
- Detailed orders and positions reports
- Real-time monitoring via dealer terminal
- Performance analytics

## REST API Endpoints (Standard Trading Operations)

### Authentication
- POST /auth/login - User authentication
- POST /auth/refresh - Token refresh
- GET /auth/validate - Validate token

### Accounts
- GET /accounts - List all accounts
- POST /accounts - Create new account
- GET /accounts/{id} - Get account details
- PUT /accounts/{id} - Update account
- DELETE /accounts/{id} - Delete account
- GET /accounts/{id}/balance - Get account balance
- GET /accounts/{id}/equity - Get account equity

### Positions
- GET /positions - List all positions
- GET /positions/{id} - Get position details
- POST /positions - Open new position
- PUT /positions/{id} - Modify position
- DELETE /positions/{id} - Close position
- GET /positions/summary - Positions summary

### Orders
- GET /orders - List all orders
- POST /orders - Create new order
- GET /orders/{id} - Get order details
- PUT /orders/{id} - Modify order
- DELETE /orders/{id} - Cancel order
- GET /orders/history - Order history

### Trading
- POST /trades/market - Execute market order
- POST /trades/limit - Place limit order
- POST /trades/stop - Place stop order
- POST /trades/close - Close trade
- GET /trades/history - Trade history

### Instruments
- GET /instruments - List available instruments
- GET /instruments/{symbol} - Get instrument details
- GET /instruments/{symbol}/quotes - Get instrument quotes

### Reports
- GET /reports/performance - Performance report
- GET /reports/transactions - Transaction report
- GET /reports/daily - Daily summary report
