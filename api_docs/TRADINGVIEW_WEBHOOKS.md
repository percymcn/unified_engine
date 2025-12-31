# TradingView Webhook Specification

## Official Documentation
- Webhook Guide: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- Pine Script Alerts: https://www.tradingview.com/pine-script-docs/faq/alerts/

## Webhook Behavior

### HTTP Request
- Method: POST
- Content-Type: `application/json` (if message is valid JSON)
- Content-Type: `text/plain` (if message is not JSON)

### JSON Format Requirements
- Use double quotes for keys and string values
- Single quotes are not valid JSON
- Alert fires immediately when condition is met
- Message body contains the alert message with placeholders replaced

## Common JSON Structure

```json
{
  "ticker": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "sentiment": "{{strategy.market_position}}",
  "quantity": "{{strategy.order.contracts}}",
  "price": "{{close}}",
  "time": "{{timenow}}",
  "interval": "{{interval}}"
}
```

## Available Placeholders

### Basic Placeholders
- `{{ticker}}` - Symbol ticker
- `{{close}}` - Close price
- `{{open}}` - Open price
- `{{high}}` - High price
- `{{low}}` - Low price
- `{{volume}}` - Volume
- `{{time}}` - Bar time
- `{{timenow}}` - Current time
- `{{interval}}` - Chart interval/timeframe

### Strategy Placeholders
- `{{strategy.order.action}}` - BUY or SELL
- `{{strategy.order.contracts}}` - Number of contracts
- `{{strategy.order.price}}` - Order price
- `{{strategy.order.id}}` - Order ID
- `{{strategy.market_position}}` - long, short, or flat
- `{{strategy.market_position_size}}` - Position size
- `{{strategy.prev_market_position}}` - Previous position
- `{{strategy.prev_market_position_size}}` - Previous position size

### Advanced Placeholders
- `{{plot_0}}`, `{{plot_1}}`, etc. - Plot values
- `{{exchange}}` - Exchange name
- `{{syminfo.tickerid}}` - Full ticker ID

## Example Webhook Payloads

### Market Order
```json
{
  "action": "market_order",
  "ticker": "{{ticker}}",
  "side": "{{strategy.order.action}}",
  "quantity": {{strategy.order.contracts}},
  "price": {{close}},
  "timestamp": "{{timenow}}"
}
```

### Stop Loss / Take Profit
```json
{
  "action": "modify_position",
  "ticker": "{{ticker}}",
  "stop_loss": {{plot_0}},
  "take_profit": {{plot_1}},
  "timestamp": "{{timenow}}"
}
```

### Close Position
```json
{
  "action": "close_position",
  "ticker": "{{ticker}}",
  "quantity": {{strategy.market_position_size}},
  "timestamp": "{{timenow}}"
}
```

## Webhook Endpoints Structure

Your webhook URL should be structured to handle:
1. Authentication (API key in header or query param)
2. Signal routing based on user/account mapping
3. Validation of JSON structure
4. Execution of trading actions
5. Error handling and logging
