# Tradovate API Documentation

## Official Resources
- GitHub FAQ: https://github.com/tradovate/example-api-faq
- Community Forum: https://community.tradovate.com/c/api-developers/15
- API Portal: https://www.tradovatetechnologies.com/api

## API Structure
- Type: REST API with Swagger definitions
- Everything in Trader Application is built on the API
- Includes WebSocket support for real-time data

## Key Features
- Complete trading functionality
- Real-time market data
- Order management
- Account management
- Position tracking
- Historical data access

## Standard API Endpoints

### Authentication
- POST /auth/accesstokenrequest - Get access token
- POST /auth/renewaccesstoken - Renew token
- POST /auth/logout - Logout

### Accounts
- GET /account/list - List accounts
- GET /account/item - Get account details
- GET /account/find - Find account
- GET /account/ldeps - List account dependencies

### Market Data
- GET /md/getchart - Get chart data
- GET /md/getproduct - Get product info
- GET /md/gethistoricaldata - Historical data
- WS /md/subscribe - Subscribe to market data
- WS /md/unsubscribe - Unsubscribe

### Orders
- POST /order/placeorder - Place order
- POST /order/modifyorder - Modify order
- POST /order/cancelorder - Cancel order
- GET /order/list - List orders
- GET /order/item - Get order details
- GET /order/deps - Order dependencies

### Positions
- GET /position/list - List positions
- GET /position/item - Get position details
- GET /position/find - Find position

### Contracts
- GET /contract/item - Get contract
- GET /contract/find - Find contract
- GET /contract/ldeps - Contract dependencies

### Fill
- GET /fill/list - List fills
- GET /fill/item - Get fill details
- GET /fill/deps - Fill dependencies

### Cash Balance
- GET /cashbalance/getcashbalance - Get cash balance
- GET /cashbalance/list - List cash balances

### Command Reports
- GET /commandReport/list - List command reports
- GET /commandReport/item - Get command report

## WebSocket Events
- md/subscribeQuote - Subscribe to quotes
- md/subscribeDom - Subscribe to depth of market
- md/subscribeHistogram - Subscribe to histogram
- order/liquidatePosition - Liquidate position
- order/modifyOrder - Modify order notification
- order/placeOrder - Order placement notification
- order/cancelOrder - Order cancellation notification

## Order Types
- Market
- Limit
- Stop Market
- Stop Limit
- MIT (Market If Touched)
- Trailing Stop

## Time in Force Options
- Day
- GTC (Good Till Cancel)
- GTD (Good Till Date)
- FOK (Fill Or Kill)
- IOC (Immediate Or Cancel)
