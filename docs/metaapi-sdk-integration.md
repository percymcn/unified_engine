# MetaAPI SDK Integration

This document describes the MetaAPI SDK integration for MT4/MT5 trading in TradeFlow.

## Overview

TradeFlow supports MetaTrader 4 (MT4) and MetaTrader 5 (MT5) trading through the official [metaapi-cloud-sdk](https://github.com/metaapi/metaapi-python-sdk). This provides a unified cloud API for both platforms.

### Dual-Mode Architecture

The MT4 and MT5 executors support two modes:

1. **SDK Mode (Preferred)**: Uses official metaapi-cloud-sdk for cloud trading
2. **Manager API Mode (Fallback)**: Uses custom httpx implementation for self-hosted Manager API

The executors automatically select SDK mode when MetaAPI credentials are configured, falling back to Manager API if SDK connection fails.

## Configuration

### Environment Variables

```bash
# MetaAPI Cloud SDK (Preferred)
METAAPI_TOKEN=your-api-token          # Get from https://app.metaapi.cloud/token
METAAPI_ACCOUNT_ID=your-account-id    # MetaAPI account ID (provision in dashboard)
METAAPI_APPLICATION=tradeflow         # Application name (optional)

# Legacy Manager API (Fallback)
MT4_API_URL=http://localhost:8080/api
MT4_MANAGER_LOGIN=1
MT4_MANAGER_PASSWORD=manager

MT5_API_URL=http://localhost:8081/api
MT5_MANAGER_LOGIN=1
MT5_MANAGER_PASSWORD=manager
```

### Getting MetaAPI Credentials

1. Create account at https://app.metaapi.cloud
2. Generate API token from https://app.metaapi.cloud/token
3. Add your MT4/MT5 account via Dashboard:
   - Choose "MetaTrader 4" or "MetaTrader 5"
   - Enter broker server, login, and password
   - Copy the generated MetaAPI Account ID

## Supported Features

### Order Types

| Order Type | MT4 | MT5 | Method |
|------------|-----|-----|--------|
| Market Buy | Yes | Yes | `create_market_buy_order()` |
| Market Sell | Yes | Yes | `create_market_sell_order()` |
| Buy Limit | Yes | Yes | `create_limit_buy_order()` |
| Sell Limit | Yes | Yes | `create_limit_sell_order()` |
| Buy Stop | Yes | Yes | `create_stop_buy_order()` |
| Sell Stop | Yes | Yes | `create_stop_sell_order()` |
| Buy Stop Limit | No | Yes | `create_stop_limit_buy_order()` |
| Sell Stop Limit | No | Yes | `create_stop_limit_sell_order()` |

### Position Management

- Get open positions: `get_positions()`
- Modify SL/TP: `modify_position(position_id, stop_loss, take_profit)`
- Close position (full): `close_position(position_id)`
- Close position (partial): `close_position(position_id, volume=0.1)`
- Close by symbol: `close_positions_by_symbol(symbol)`

### Order Management

- Get pending orders: `get_orders()`
- Modify pending order: `modify_order(order_id, ...)`
- Cancel pending order: `cancel_order(order_id)`

### Account Information

- Get account info: `get_account_info()`
  - Balance, Equity, Margin, Free Margin
  - Leverage, Currency, Platform (mt4/mt5)
  - Server, Broker name

### Real-Time Market Data

- Subscribe to quotes: `subscribe_to_market_data(symbol)`
- Unsubscribe: `unsubscribe_from_market_data(symbol)`
- Bulk subscribe: `subscribe_to_symbols([symbols])`
- Get current quote: `get_quote(symbol)`
- Get bulk quotes: `get_quotes_bulk([symbols])`
- Get symbol spec: `get_symbol_specification(symbol)`

### Real-Time Streaming

For real-time updates, add a synchronization listener:

```python
class MyListener:
    def on_symbol_price_updated(self, instance_index, price):
        print(f"Price update: {price['symbol']} bid={price['bid']} ask={price['ask']}")

    def on_position_updated(self, instance_index, position):
        print(f"Position update: {position['id']} profit={position['profit']}")

    def on_account_information_updated(self, instance_index, account_info):
        print(f"Account update: equity={account_info['equity']}")

# Add listener
service.add_synchronization_listener(MyListener())
```

## Usage Examples

### Basic Trading

```python
from app.services.metaapi_sdk_service import MetaAPISDKService

# Initialize service
service = MetaAPISDKService(
    token="your-token",
    account_id="your-account-id"
)

# Connect
await service.connect()

# Get account info
info = await service.get_account_info()
print(f"Balance: {info['balance']} {info['currency']}")

# Place market order
result = await service.create_market_buy_order(
    symbol="EURUSD",
    volume=0.1,
    stop_loss=1.0800,
    take_profit=1.1000,
    comment="TradeFlow signal"
)

if result["success"]:
    print(f"Order placed: {result['order_id']}")

# Disconnect
await service.disconnect()
```

### Using MT4/MT5 Executors

```python
from app.brokers.mt4_executor import MT4Executor
from app.brokers.mt5_executor import MT5Executor

# MT4 with MetaAPI
executor = MT4Executor(
    metaapi_token="your-token",
    metaapi_account_id="your-account-id"
)

await executor.initialize()

# Check mode
if executor.is_using_sdk:
    print("Using MetaAPI SDK")
else:
    print("Using Manager API fallback")

# Place order (same API regardless of mode)
from app.models.pydantic_schemas import OrderRequest

order = OrderRequest(
    account_id="123",
    symbol="EURUSD",
    order_type="market_buy",
    quantity=0.1,
    stop_loss=1.0800,
    take_profit=1.1000
)

response = await executor.place_order(order)
```

### Using Adapters (Domain Layer)

```python
from app.infrastructure.adapters.mt4_adapter import MT4Adapter

adapter = MT4Adapter(
    metaapi_token="your-token",
    metaapi_account_id="your-account-id"
)

# Authenticate
await adapter.authenticate({
    "metaapi_token": "your-token",
    "metaapi_account_id": "your-account-id"
})

# Get positions
positions = await adapter.get_positions()
```

## Architecture

```
+------------------+     +------------------+
|  Signal Router   |     |  Dashboard UI    |
+--------+---------+     +--------+---------+
         |                        |
         v                        v
+------------------+     +------------------+
|  MT4/MT5 Adapter |     |  API Endpoints   |
+--------+---------+     +--------+---------+
         |                        |
         v                        v
+----------------------------------------+
|           MT4/MT5 Executor             |
|  (dual-mode: SDK preferred, httpx fb) |
+-------------------+--------------------+
                    |
    +---------------+---------------+
    |                               |
    v                               v
+------------------+     +------------------+
| MetaAPISDKService|     | httpx Manager API|
| (cloud trading)  |     | (self-hosted)    |
+------------------+     +------------------+
```

## Limitations

### MetaAPI Free Tier
- 1 account
- Basic features only
- Rate limits apply

### SDK-Specific
- Stop-limit orders only on MT5
- Some brokers may have additional restrictions
- Network latency for cloud connection

### Manager API Fallback
- Requires self-hosted Manager API bridge
- Limited feature set
- No real-time streaming

## Troubleshooting

### Connection Issues

```python
# Check health status
status = service.health_status
print(f"Connected: {status['connected']}")
print(f"Synchronized: {status['synchronized']}")
```

### SDK Not Available

If SDK is not installed:
```bash
pip install metaapi-cloud-sdk>=29.0.0
```

Check availability:
```python
from app.services.metaapi_sdk_service import SDK_AVAILABLE
print(f"SDK Available: {SDK_AVAILABLE}")
```

### Authentication Errors

- Verify METAAPI_TOKEN is valid and not expired
- Verify METAAPI_ACCOUNT_ID matches your provisioned account
- Check MetaAPI dashboard for account status
- Ensure account is deployed (not undeployed)

## References

- [MetaAPI Documentation](https://metaapi.cloud/docs/)
- [Python SDK GitHub](https://github.com/metaapi/metaapi-python-sdk)
- [MetaAPI Dashboard](https://app.metaapi.cloud/)
