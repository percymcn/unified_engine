# ProjectX / TopStep API Documentation

## Official Sources
- ProjectX Gateway API: https://gateway.docs.projectx.com/
- TopStepX API: https://help.topstep.com/en/articles/11187768-topstepx-api-access

## API Access

### Subscription
- Cost: $29/month (or $14.50/month with code "topstep" for Topstep Traders)
- Includes: API token, REST and WebSocket APIs, real-time market data, documentation

### Limitations
- No sandbox environment currently available
- No technical support for coding/implementation

## API Features

### REST API
- Compatible with Python, Java, .NET, JavaScript
- Real-time market data access
- Account management
- Position tracking
- Order execution

### WebSocket API
- Real-time data streaming
- Account updates
- Position changes
- Order fill notifications

## Standard Endpoints (Based on Trading Platform Standards)

### Authentication
- POST /auth/token - Get access token
- POST /auth/refresh - Refresh token
- GET /auth/validate - Validate token

### Accounts
- GET /accounts - List funded accounts
- GET /accounts/{id} - Get account details
- GET /accounts/{id}/balance - Account balance
- GET /accounts/{id}/performance - Account performance metrics

### Evaluation
- GET /evaluations - List evaluations
- GET /evaluations/{id} - Evaluation details
- GET /evaluations/{id}/progress - Evaluation progress
- GET /evaluations/{id}/rules - Evaluation rules
- GET /evaluations/{id}/metrics - Performance metrics

### Positions
- GET /positions - List open positions
- GET /positions/{id} - Position details
- POST /positions - Open position
- PUT /positions/{id} - Modify position
- DELETE /positions/{id} - Close position

### Orders
- GET /orders - List orders
- POST /orders - Create order
- GET /orders/{id} - Order details
- PUT /orders/{id} - Modify order
- DELETE /orders/{id} - Cancel order
- GET /orders/history - Order history

### Market Data
- GET /instruments - Available instruments
- GET /instruments/{symbol}/quote - Current quote
- GET /instruments/{symbol}/chart - Chart data
- WS /stream/quotes - Real-time quotes stream
- WS /stream/bars - Real-time bars stream

### Risk Management
- GET /accounts/{id}/risk - Risk metrics
- GET /accounts/{id}/limits - Account limits
- GET /accounts/{id}/violations - Rule violations

### Reports
- GET /reports/daily - Daily performance
- GET /reports/transactions - Transaction history
- GET /reports/pnl - Profit & loss report
