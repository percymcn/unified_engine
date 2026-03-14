# FlowAlgo Confluence Webhook Proxy

Automated options flow scraper that acts as a smart filter between TradingView alerts and your trading webhook. Only forwards signals when there's confluence with institutional options flow from FlowAlgo.

## Features

- **Headless Browser Scraping**: Uses Playwright to scrape FlowAlgo in real-time
- **Smart Filtering**: Only forwards TradingView alerts when matching options flow is detected
- **Ticker Mapping**: Automatically maps futures tickers (MES/MYM → SPY, NQ → QQQ, etc.)
- **Confluence Detection**: Checks for bullish/bearish flow alignment within 5-minute window
- **Production Ready**: Error handling, retry logic, systemd integration
- **Logging**: Comprehensive logging to file and stdout

## How It Works

```
TradingView Alert → http://your-ip:9001/filter → Check FlowAlgo → Forward if confluence → mytradeflow.app
                                                         ↓
                                                    No match? Skip.
```

## Requirements

```bash
# Python 3.8+
pip install playwright flask python-dotenv requests

# Install Chromium browser
playwright install chromium
```

## Setup

### 1. Configuration

Copy the example .env file and configure:

```bash
cp .env.flow_example .env
nano .env
```

Required settings:
```env
FLOW_EMAIL=your-flowalgo-email@example.com
FLOW_PASS=your-flowalgo-password
MYTRADEFLOW_WEBHOOK=https://mytradeflow.app/webhooks/your-actual-webhook-key
```

### 2. Test Run

```bash
# Make executable
chmod +x flow_confluence_proxy.py

# Test run
python3 flow_confluence_proxy.py
```

You should see:
```
FlowAlgo Confluence Webhook Proxy Starting...
Flask server: http://0.0.0.0:9001
Tracking tickers: SPY, QQQ, GLD
Starting polling loop...
Browser initialized
✓ Successfully logged in to FlowAlgo
```

### 3. Systemd Service (Production)

```bash
# Copy service file
sudo cp flow_confluence_proxy.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable flow_confluence_proxy
sudo systemctl start flow_confluence_proxy

# Check status
sudo systemctl status flow_confluence_proxy

# View logs
sudo journalctl -u flow_confluence_proxy -f
tail -f confluence.log
```

## Usage

### TradingView Webhook Setup

In your TradingView alert, set the webhook URL to:

```
http://your-server-ip:9001/filter
```

Alert message (JSON):
```json
{
  "ticker": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "price": {{close}},
  "timestamp": "{{timenow}}"
}
```

### Ticker Mapping

The proxy automatically maps futures tickers to their equity proxies:

| TradingView | FlowAlgo Proxy | Description |
|-------------|----------------|-------------|
| MES, MYM    | SPY            | S&P 500     |
| NQ, MNQ     | QQQ            | Nasdaq 100  |
| GC, MGC     | GLD            | Gold        |

**Note:** Bitcoin/crypto options (BTC, ETH) are not supported as FlowAlgo focuses on equity/ETF options. Deribit/CME crypto options are not covered.

### Confluence Logic

**BUY Signal** requires one of:
- Bullish call sweep/block on proxy ticker
- Bearish put sweep/block (protective puts)

**SELL Signal** requires one of:
- Bearish call sweep/block on proxy ticker
- Bullish put sweep/block

Minimum premium: $50,000
Time window: Last 5 minutes

## API Endpoints

### POST /filter
Main webhook endpoint for TradingView alerts.

**Request:**
```json
{
  "ticker": "MES",
  "action": "buy",
  "price": 5500
}
```

**Response (confluence found):**
```json
{
  "status": "forwarded",
  "confluence": {
    "ticker": "SPY",
    "side": "bullish",
    "type": "call",
    "premium": 125000,
    "flow_type": "sweep"
  },
  "mytradeflow_response": 200
}
```

**Response (no confluence):**
```json
{
  "status": "skipped",
  "reason": "no flow confluence",
  "checked_ticker": "SPY",
  "tv_action": "buy"
}
```

### GET /health
Health check endpoint.

```bash
curl http://localhost:9001/health
```

**Response:**
```json
{
  "status": "ok",
  "logged_in": true,
  "last_scrape": "2026-03-05T12:34:56",
  "flow_entries": 47
}
```

### GET /recent
View recent flow entries (debugging).

```bash
# All recent flow
curl http://localhost:9001/recent

# Specific ticker, last 10 minutes
curl "http://localhost:9001/recent?ticker=SPY&minutes=10"
```

**Response:**
```json
{
  "count": 3,
  "entries": [
    {
      "ticker": "SPY",
      "side": "bullish",
      "type": "call",
      "flow_type": "sweep",
      "premium": 125000,
      "strike": 550,
      "timestamp": "2026-03-05T12:30:00"
    }
  ]
}
```

## Monitoring

### Check if scraping is working

```bash
# View recent flow
curl http://localhost:9001/recent | jq

# Check logs
tail -f confluence.log | grep -E "CONFLUENCE|Parsed"
```

### Common log patterns

```
✓ CONFLUENCE: TV buy + SPY bullish call sweep $125,000
✗ No confluence: TV buy vs 0 SPY flows
Parsed 12 qualifying flow entries
Next scrape in 45s...
```

## Troubleshooting

### Login fails

1. Check credentials in `.env`
2. Verify FlowAlgo subscription is active
3. Check if FlowAlgo changed their login page structure

```bash
# Enable debug logging
# In flow_confluence_proxy.py, change:
logging.basicConfig(level=logging.DEBUG)
```

### No flow entries parsed

The FlowAlgo page structure may have changed. You need to inspect the page and update selectors in `_parse_flow_table()`:

```bash
# Run Playwright in headed mode to see the page
# In flow_confluence_proxy.py, change:
self.browser = await playwright.chromium.launch(headless=False)
```

**Common FlowAlgo DOM patterns (as of 2026):**
- Flow rows: `.flow-item`, `.activity-row`, `[data-order-id]`
- Ticker: `.symbol`, `.ticker`, `div[class*="ticker"]`
- Premium: `.premium`, `.size`, text like "$1.25M"
- Type: `.sweep`, `.block`, `.alert-type`
- Side: `.bullish`/`.bearish`, or infer from call/put + direction

Use browser DevTools (F12) → Inspect element on the flow table after login to get exact selectors.

Then update the CSS selectors in the code:
- Ticker: `ticker_elem = await row.query_selector('[data-ticker], .ticker, .symbol')`
- Flow type: `type_elem = await row.query_selector('[data-type], .flow-type, .alert-type')`
- Side: `side_elem = await row.query_selector('[data-side], .side, .bullish, .bearish')`
- Premium: `premium_elem = await row.query_selector('[data-premium], .premium, .size')`

### Webhook not forwarding

Check confluence logic:

```bash
# Test webhook
curl -X POST http://localhost:9001/filter \
  -H "Content-Type: application/json" \
  -d '{"ticker":"MES","action":"buy","price":5500}'

# Check recent flow
curl "http://localhost:9001/recent?ticker=SPY&minutes=5" | jq
```

## Security Notes

- Store credentials in `.env`, never commit to git
- Use firewall to restrict Flask port 9001 to TradingView IPs only
- Run as non-root user (systemd service does this)
- Monitor logs for failed login attempts

## Performance

- Polls FlowAlgo every 30-60 seconds with random delays
- Stores last 1000 flow entries in memory
- Webhook response time: <100ms (no external calls if no confluence)
- Memory usage: ~150-200 MB (Chromium + Python)

## License

MIT License - Use at your own risk. This script scrapes a third-party website which may violate their ToS. Verify compliance before use.

## Support

For issues with:
- FlowAlgo scraping: Update selectors in `_parse_flow_table()`
- Webhook forwarding: Check `MYTRADEFLOW_WEBHOOK` in `.env`
- Confluence logic: Adjust in `flow_store.check_confluence()`

Logs are your friend: `tail -f confluence.log`
