# MetaTrader 4 & 5 API Documentation

## Official Resources
- MT4 API: https://www.metatrader4.com/en/brokers/api
- MT5 Integration Options: https://www.metatrader5.com/

## Third-Party API Solutions

### Manager API
- MT4 ManagerAPI .NET Wrapper: https://confluence.cplugin.com/display/MT4ManAPIWrapper
- Dev4Traders REST API: https://dev4traders.com/docs/metatrader-manager-rest-api/
- Kenmore Design MT4 JSON API: https://www.kenmoredesign.com/solutions/mt4-api-json/
- MTAPInet Online:  https://mtapi.online/

### Connection Modes
1. **Normal Mode** - Request/Response (like MT4 Administrator)
2. **Pumping Mode** - Real-time data streaming (like MT4 Manager)
3. **Dealing Mode** - Process client requests

## Manager API Functions

### Account Management
- UserAdd - Create new user account
- UserUpdate - Update user information
- UserDelete - Delete user account
- UserRecord - Get user details
- UserPasswordCheck - Validate password
- UserRecordNew - Get updated user record

### Trading Operations
- TradeTransaction - Execute trade operation
- TradeBalance - Modify account balance
- TradeCredit - Add/remove credit
- HistoryGet - Get trade history
- TradesGet - Get open trades
- TradesRequest - Get trade requests

### Order Management
- OrderUpdate - Modify order
- OrderDelete - Delete pending order
- OrderGet - Get order details

### Position Tracking
- TradesUserHistory - User trade history
- ExposureGet - Get exposure data
- MarginLevelGet - Get margin level

### Symbol/Market Data
- SymbolsGetAll - Get all symbols
- SymbolGet - Get symbol details
- SymbolSet - Update symbol settings
- QuoteGet - Get current quote
- ChartRequest - Request chart data

### Risk Management
- MarginLevelRequest - Check margin level
- GroupsRequest - Get trading groups
- ManagerRightsGet - Get manager rights

## Web API Endpoints (REST Wrapper)

### Authentication
- POST /api/auth/login - Login to MT4/MT5 server
- POST /api/auth/logout - Logout
- GET /api/auth/validate - Validate session

### Users
- GET /api/users - List users
- POST /api/users - Create user
- GET /api/users/{login} - Get user details
- PUT /api/users/{login} - Update user
- DELETE /api/users/{login} - Delete user
- PUT /api/users/{login}/password - Change password
- POST /api/users/{login}/balance - Modify balance

### Trades
- GET /api/trades - Get open trades
- POST /api/trades - Execute trade
- GET /api/trades/{ticket} - Get trade details
- PUT /api/trades/{ticket} - Modify trade
- DELETE /api/trades/{ticket} - Close trade
- GET /api/trades/history - Trade history

### Orders
- GET /api/orders - Get pending orders
- POST /api/orders - Create order
- GET /api/orders/{ticket} - Get order details
- PUT /api/orders/{ticket} - Modify order
- DELETE /api/orders/{ticket} - Delete order

### Market Data
- GET /api/symbols - List symbols
- GET /api/symbols/{symbol}/quote - Get quote
- GET /api/symbols/{symbol}/history - Historical data
- GET /api/ticks/{symbol} - Get ticks

### Reports
- GET /api/reports/balance - Balance report
- GET /api/reports/equity - Equity report
- GET /api/reports/exposure - Exposure report
- GET /api/reports/margin - Margin report

## Trade Operation Constants

### Order Types
- OP_BUY = 0 - Buy market order
- OP_SELL = 1 - Sell market order
- OP_BUY_LIMIT = 2 - Buy limit order
- OP_SELL_LIMIT = 3 - Sell limit order
- OP_BUY_STOP = 4 - Buy stop order
- OP_SELL_STOP = 5 - Sell stop order

### Trade Commands
- OP_BUY = 0
- OP_SELL = 1
- OP_CLOSE = 2
- OP_MODIFY = 3
- OP_DELETE = 4
