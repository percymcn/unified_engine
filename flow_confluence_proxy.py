#!/home/pharma5/unified_engine/flow_venv/bin/python3
"""
FlowAlgo Confluence Webhook Proxy
Scrapes FlowAlgo options flow and filters TradingView alerts based on confluence.
Only forwards signals to mytradeflow.app when matching flow is detected.

Requirements:
- playwright (playwright install chromium)
- flask
- python-dotenv

Setup:
1. Create .env file with FLOW_EMAIL and FLOW_PASS
2. Install: pip install playwright flask python-dotenv
3. Run: playwright install chromium
4. Start: python3 flow_confluence_proxy.py

Systemd service:
sudo cp flow_confluence_proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable flow_confluence_proxy
sudo systemctl start flow_confluence_proxy
"""

import os
import sys
import asyncio
import logging
import threading
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import deque

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Load environment variables
load_dotenv()

# Configuration
FLOW_EMAIL = os.getenv('FLOW_EMAIL')
FLOW_PASS = os.getenv('FLOW_PASS')
MYTRADEFLOW_WEBHOOK = os.getenv('MYTRADEFLOW_WEBHOOK', 'https://mytradeflow.app/your-webhook-endpoint')
FLASK_PORT = int(os.getenv('FLASK_PORT', '9001'))
POLL_INTERVAL_MIN = int(os.getenv('POLL_INTERVAL_MIN', '30'))
POLL_INTERVAL_MAX = int(os.getenv('POLL_INTERVAL_MAX', '60'))
RANDOM_DELAY_MIN = int(os.getenv('RANDOM_DELAY_MIN', '5'))
RANDOM_DELAY_MAX = int(os.getenv('RANDOM_DELAY_MAX', '10'))
LOG_FILE = os.getenv('LOG_FILE', 'confluence.log')
CONFLUENCE_WINDOW_MINUTES = int(os.getenv('CONFLUENCE_WINDOW_MINUTES', '5'))
MIN_PREMIUM = int(os.getenv('MIN_PREMIUM', '50000'))

# Ticker mapping: TradingView -> FlowAlgo proxy ticker
TICKER_MAP = {
    'MES': 'SPY',
    'MYM': 'SPY',
    'NASDAQ': 'QQQ',
    'NQ': 'QQQ',
    'MNQ': 'QQQ',
    'GOLD': 'GLD',
    'GC': 'GLD',
    'MGC': 'GLD',
}

# Target tickers to track
# Core ETFs that map to futures
TARGET_TICKERS = ['SPY', 'QQQ', 'GLD', 'IWM', 'DIA']

# Correlated/leveraged ETFs (sentiment amplifiers)
CORRELATED_TICKERS = ['TQQQ', 'SQQQ', 'TNA', 'TZA', 'SPXL', 'SPXU', 'UVXY', 'VIX']

# Major tech movers that influence indices
TECH_MOVERS = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

# All tickers to track
ALL_TRACKED_TICKERS = TARGET_TICKERS + CORRELATED_TICKERS + TECH_MOVERS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)


@dataclass
class FlowEntry:
    """Represents a single options flow entry"""
    timestamp: datetime
    ticker: str
    flow_type: str  # 'sweep' or 'block'
    side: str  # 'bullish' or 'bearish'
    option_type: str  # 'call' or 'put'
    premium: float
    strike: float
    expiry: str
    raw_data: Dict[str, Any]


class FlowDataStore:
    """Thread-safe storage for recent flow entries"""

    def __init__(self, max_age_minutes: int = 10):
        self.entries: deque = deque(maxlen=1000)
        self.max_age = timedelta(minutes=max_age_minutes)
        self.lock = threading.Lock()

    def add_entry(self, entry: FlowEntry):
        """Add a new flow entry"""
        with self.lock:
            self.entries.append(entry)
            logger.debug(f"Added flow: {entry.ticker} {entry.side} {entry.option_type} ${entry.premium:,.0f}")

    def get_recent_entries(self, ticker: str, minutes: int = 5) -> List[FlowEntry]:
        """Get recent entries for a ticker within the time window"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        with self.lock:
            return [
                e for e in self.entries
                if e.ticker == ticker and e.timestamp >= cutoff
            ]

    def check_confluence(self, ticker: str, tv_action: str, minutes: int = 5) -> Optional[FlowEntry]:
        """
        Check if there's confluence between TV signal and recent flow.

        Args:
            ticker: Mapped ticker (SPY, QQQ, GLD)
            tv_action: 'buy' or 'sell' from TradingView
            minutes: Time window to check

        Returns:
            Matching FlowEntry if confluence found, None otherwise
        """
        recent = self.get_recent_entries(ticker, minutes)

        if not recent:
            logger.info(f"No recent flow for {ticker} in last {minutes}m")
            return None

        # Map TV action to expected flow characteristics
        if tv_action.lower() in ('buy', 'long'):
            # Look for bullish flow:
            # - Bullish call sweeps/blocks = directional bet on upside
            # - Bearish puts (high premium) = hedging downside but often precedes upside if aggressive
            for entry in recent:
                if entry.side == 'bullish' and entry.option_type == 'call':
                    logger.info(f"✓ CONFLUENCE: TV buy + {ticker} bullish call sweep ${entry.premium:,.0f}")
                    return entry
                if entry.side == 'bearish' and entry.option_type == 'put':
                    logger.info(f"✓ CONFLUENCE: TV buy + {ticker} bearish put (protective hedge) ${entry.premium:,.0f}")
                    return entry

        elif tv_action.lower() in ('sell', 'short', 'close'):
            # Look for bearish flow (bearish calls or bullish puts)
            for entry in recent:
                if entry.side == 'bearish' and entry.option_type == 'call':
                    logger.info(f"✓ CONFLUENCE: TV sell + {ticker} bearish call ${entry.premium:,.0f}")
                    return entry
                if entry.side == 'bullish' and entry.option_type == 'put':
                    logger.info(f"✓ CONFLUENCE: TV sell + {ticker} bullish put ${entry.premium:,.0f}")
                    return entry

        logger.info(f"✗ No confluence: TV {tv_action} vs {len(recent)} {ticker} flows")
        return None


# Global flow data store
flow_store = FlowDataStore(max_age_minutes=10)


class FlowAlgoScraper:
    """Scrapes FlowAlgo using Playwright"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        self.last_scrape = None
        self.retry_count = 0
        self.max_retries = 3

    async def initialize(self):
        """Initialize browser and login"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            # Rotate user agents to avoid detection
            user_agents = [
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=random.choice(user_agents)
            )
            self.page = await self.context.new_page()
            logger.info("Browser initialized")

            await self.login()

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}", exc_info=True)
            raise

    async def login(self):
        """Login to FlowAlgo"""
        if not FLOW_EMAIL or not FLOW_PASS:
            raise ValueError("FLOW_EMAIL and FLOW_PASS must be set in .env")

        try:
            logger.info("Attempting login to FlowAlgo...")
            await self.page.goto('https://app.flowalgo.com/login', wait_until='networkidle', timeout=30000)

            # Save screenshot for debugging
            await self.page.screenshot(path='login_page.png')
            logger.info("Screenshot saved to login_page.png")

            # Get page content for debugging
            content = await self.page.content()
            logger.debug(f"Page title: {await self.page.title()}")

            # Try multiple selector patterns for email field
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email" i]',
                'input[id="email"]',
                '#email',
                '[data-testid="email"]',
                'input[autocomplete="email"]'
            ]

            email_input = None
            for selector in email_selectors:
                try:
                    email_input = await self.page.wait_for_selector(selector, timeout=2000)
                    logger.info(f"Found email input with selector: {selector}")
                    break
                except:
                    continue

            if not email_input:
                logger.error("Could not find email input field with any selector")
                raise Exception("Email input not found")

            # Fill email
            await self.page.fill(selector, FLOW_EMAIL)
            logger.info("Filled email field")

            # Find and fill password
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="password" i]',
                'input[id="password"]',
                '#password'
            ]

            password_input = None
            for sel in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(sel, timeout=2000)
                    logger.info(f"Found password input with selector: {sel}")
                    await self.page.fill(sel, FLOW_PASS)
                    logger.info("Filled password field")
                    break
                except:
                    continue

            if not password_input:
                raise Exception("Password input not found")

            # Find and click login button
            button_selectors = [
                'button[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign In")',
                'button:has-text("Log In")',
                'input[type="submit"]',
                '[data-testid="login-button"]',
                '.login-button',
                '#login-button'
            ]

            for btn_sel in button_selectors:
                try:
                    await self.page.click(btn_sel, timeout=2000)
                    logger.info(f"Clicked login button: {btn_sel}")
                    break
                except:
                    continue

            # Wait a bit for page transition
            await asyncio.sleep(3)

            # Dismiss any popup dialogs (Terms of Service, Chat Code of Conduct, etc.)
            try:
                popup_buttons = [
                    'button:has-text("OK, GOT IT")',
                    'button:has-text("OK")',
                    'button:has-text("Accept")',
                    'button:has-text("I Agree")',
                    'button:has-text("Close")',
                    '.modal button',
                    '[role="dialog"] button',
                ]
                for selector in popup_buttons:
                    try:
                        btn = self.page.locator(selector).first
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                            logger.info(f"Dismissed popup with selector: {selector}")
                            await asyncio.sleep(1)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"No popups to dismiss: {e}")

            # Save post-login screenshot
            await self.page.screenshot(path='post_login.png')
            logger.info("Post-login screenshot saved to post_login.png")
            logger.info(f"Current URL: {self.page.url}")
            logger.info(f"Page title: {await self.page.title()}")

            # Check for actual login form error messages (not general page text)
            # Only look for errors in login form context, not entire page
            login_form_visible = False
            try:
                login_form = self.page.locator('form[action*="login"], .login-form, #login-form')
                login_form_visible = await login_form.is_visible(timeout=1000)
            except:
                pass

            if login_form_visible:
                error_msg = self.page.locator('.error, .alert-danger, .login-error')
                try:
                    if await error_msg.is_visible(timeout=1000):
                        error_text = await error_msg.text_content()
                        logger.error(f"Login form error: {error_text}")
                        raise Exception("Login credentials rejected")
                except:
                    pass

            # Check if we're logged in (not on login page anymore)
            current_url = self.page.url
            if '/login' in current_url.lower():
                logger.error("Still on login page - login may have failed")
                raise Exception("Login failed - still on login page")

            # If we're on app.flowalgo.com and not on login page, assume success
            if 'app.flowalgo.com' in current_url and '/login' not in current_url.lower():
                logger.info(f"Login appears successful - on {current_url}")
            else:
                logger.warning(f"Unexpected URL after login: {current_url}")

            self.logged_in = True
            self.retry_count = 0
            logger.info("✓ Successfully logged in to FlowAlgo")

        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            self.logged_in = False
            raise

    async def scrape_dashboard(self) -> List[FlowEntry]:
        """Scrape the latest flow entries from dashboard"""
        if not self.logged_in:
            logger.warning("Not logged in, attempting re-login...")
            await self.login()

        try:
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")

            # Try using the FlowAlgo export API page (cleaner than dashboard scraping)
            # Based on: https://github.com/SC4RECOIN/FlowAlgo-Options-Trader
            export_url = 'https://app.flowalgo.com/options-export-beta/'

            logger.info(f"Navigating to export page: {export_url}")
            await self.page.goto(export_url, wait_until='networkidle', timeout=15000)
            await asyncio.sleep(3)

            # Check for session expiry
            page_content = await self.page.content()
            if any(text in page_content.lower() for text in ['session expired', 'please log in', 'login required']):
                logger.warning("Session expired, re-logging in...")
                self.logged_in = False
                await self.login()
                return []

            # Fill in the export form filters
            logger.info("Filling export form with our target tickers...")

            # Fill symbols field
            try:
                symbols_input = await self.page.wait_for_selector('input[placeholder*="Symbols" i], input[name*="symbol" i]', timeout=5000)
                await symbols_input.fill('')  # Clear existing
                await symbols_input.type('SPY,QQQ,GLD', delay=50)
                logger.info("✓ Filled symbols: SPY,QQQ,GLD")
            except Exception as e:
                logger.warning(f"Could not fill symbols field: {e}")

            # Fill minimum premium field
            try:
                premium_input = await self.page.wait_for_selector('input[placeholder*="Premium" i], input[name*="premium" i]', timeout=5000)
                await premium_input.fill('')
                await premium_input.type(str(MIN_PREMIUM), delay=50)
                logger.info(f"✓ Filled min premium: ${MIN_PREMIUM:,}")
            except Exception as e:
                logger.warning(f"Could not fill premium field: {e}")

            # Click "Get Data" button
            try:
                get_data_btn = await self.page.wait_for_selector('button:has-text("Get Data"), input[value*="Get Data"]', timeout=5000)
                await get_data_btn.click()
                logger.info("✓ Clicked 'Get Data' button")

                # Wait for results to load
                await asyncio.sleep(5)
                logger.info("Waiting for results table to populate...")
            except Exception as e:
                logger.warning(f"Could not click Get Data button: {e}")

            # Save screenshot to verify data loaded
            await self.page.screenshot(path='page_export_results.png')
            logger.info("Screenshot saved: page_export_results.png")

            # The export table has a clean structure, much easier to parse!
            logger.info("Parsing export results table...")

            # Give the table time to populate after clicking Get Data
            await asyncio.sleep(3)

            # Parse flow rows
            entries = await self._parse_flow_table()

            self.last_scrape = datetime.now()
            self.retry_count = 0

            return entries

        except Exception as e:
            logger.error(f"Scrape failed: {e}", exc_info=True)
            self.retry_count += 1

            if self.retry_count >= self.max_retries:
                logger.error("Max retries reached, re-initializing...")
                self.logged_in = False
                await self.close()
                await self.initialize()

            return []

    async def _parse_flow_table(self) -> List[FlowEntry]:
        """Parse flow entries from the export table using JavaScript evaluation"""
        entries = []

        try:
            # The export table has a clean, predictable structure with columns:
            # DATE | TIME | TICKER | EXPIRY | STRIKE | C/P | SPOT | QTY | PRICE | TYPE | VOLUME | OI | PREMIUM | SECTOR | UNUSUAL
            flow_data = await self.page.evaluate('''() => {
                const flows = [];
                const debug = {
                    tableRows: 0,
                    dataRows: 0,
                    parsedRows: 0
                };

                // Find all table rows (skip header row)
                const rows = document.querySelectorAll('table tr');
                debug.tableRows = rows.length;

                rows.forEach((row, index) => {
                    // Skip header row (first row)
                    if (index === 0) return;

                    const cells = row.querySelectorAll('td');
                    if (cells.length < 10) return;  // Need at least 10 columns

                    debug.dataRows++;

                    // Extract data from cells
                    // Based on the export table structure we saw in the screenshot
                    const ticker = cells[2]?.innerText?.trim() || '';  // TICKER column
                    const expiry = cells[3]?.innerText?.trim() || '';   // EXPIRY column
                    const strike = cells[4]?.innerText?.trim() || '';   // STRIKE column
                    const callPut = cells[5]?.innerText?.trim() || '';  // C/P column
                    const flowType = cells[9]?.innerText?.trim() || ''; // TYPE column (SWEEP/BLOCK/SPLIT)
                    const premium = cells[12]?.innerText?.trim() || ''; // PREMIUM column

                    // Filter for our target tickers
                    const targetTickers = ['SPY', 'QQQ', 'GLD', 'IWM', 'DIA', 'TQQQ', 'SQQQ', 'TNA', 'TZA', 'SPXL', 'SPXU', 'UVXY', 'VIX', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'];
                    if (!targetTickers.includes(ticker)) return;

                    // Filter for SWEEP or BLOCK only (not SPLIT)
                    if (flowType !== 'SWEEP' && flowType !== 'BLOCK') return;

                    debug.parsedRows++;

                    flows.push({
                        ticker: ticker,
                        flowType: flowType,
                        strike: strike,
                        expiry: expiry,
                        callPut: callPut,
                        premium: premium,
                        rowText: Array.from(cells).map(c => c.innerText).join(' | ').substring(0, 300)
                    });
                });

                return { flows, debug };
            }''')

            # Extract flows and debug info
            flows_found = flow_data.get('flows', [])
            debug_info = flow_data.get('debug', {})

            logger.info(f"JavaScript debug: {debug_info}")
            logger.info(f"JavaScript extraction found {len(flows_found)} potential flow rows")

            if flows_found:
                logger.info(f"Sample flow data: {flows_found[0]}")

                # Save sample for debugging
                with open('flow_data_sample.json', 'w') as f:
                    import json
                    json.dump({'flows': flows_found[:10], 'debug': debug_info}, f, indent=2)
                logger.info("Saved sample flow data to flow_data_sample.json")

                # Parse the extracted export table data into FlowEntry objects
                # Export table provides clean structured data!
                for item in flows_found:
                    try:
                        ticker = item['ticker']
                        flow_type = item['flowType'].lower()
                        strike_str = item['strike']
                        expiry = item['expiry']
                        call_put = item['callPut'].upper()
                        premium_str = item['premium']

                        # Determine option type from C/P column
                        if 'CALL' in call_put:
                            option_type = 'call'
                        elif 'PUT' in call_put:
                            option_type = 'put'
                        else:
                            logger.debug(f"Unknown option type: {call_put}")
                            continue

                        # Parse premium
                        premium = self._parse_premium(premium_str)
                        if premium < MIN_PREMIUM:
                            continue

                        # Parse strike price
                        try:
                            strike = float(strike_str.replace(',', ''))
                        except:
                            strike = 0.0

                        # Determine bullish/bearish based on option type
                        # Calls are generally bullish, Puts are generally bearish
                        # (This is a simplification - real sentiment depends on more factors)
                        side = 'bullish' if option_type == 'call' else 'bearish'

                        entry = FlowEntry(
                            timestamp=datetime.now(),
                            ticker=ticker,
                            flow_type=flow_type,
                            side=side,
                            option_type=option_type,
                            premium=premium,
                            strike=strike,
                            expiry=expiry,
                            raw_data=item  # Store the full export row data
                        )

                        entries.append(entry)
                        logger.info(f"✓ Parsed flow: {ticker} {flow_type} {option_type} ${premium:,.0f} strike={strike} {side}")

                    except Exception as e:
                        logger.warning(f"Failed to parse flow item: {e}")
                        import traceback
                        logger.warning(traceback.format_exc())
                        continue

            # If JavaScript extraction succeeded, return those entries
            if entries:
                logger.info(f"Parsed {len(entries)} qualifying flow entries from JavaScript extraction")
                return entries

            # Otherwise, try the traditional selector approach as fallback
            logger.info("JavaScript extraction didn't yield entries, trying traditional selectors...")
            rows = await self.page.query_selector_all('table tbody tr, table tr, .flow-row, .activity-row, [class*="flow-"]')

            for row in rows[:50]:  # Process latest 50 rows
                try:
                    # Extract data from row - ADJUST THESE SELECTORS based on actual page structure
                    ticker_elem = await row.query_selector('[data-ticker], .ticker, td:nth-child(1)')
                    ticker = await ticker_elem.inner_text() if ticker_elem else None

                    if not ticker or ticker.strip() not in ALL_TRACKED_TICKERS:
                        continue

                    # Parse flow type (sweep/block)
                    type_elem = await row.query_selector('[data-type], .flow-type, td:nth-child(2)')
                    flow_type = await type_elem.inner_text() if type_elem else ''
                    flow_type = flow_type.lower().strip()

                    if flow_type not in ('sweep', 'block'):
                        continue

                    # Parse side (bullish/bearish)
                    side_elem = await row.query_selector('[data-side], .side, td:nth-child(3)')
                    side = await side_elem.inner_text() if side_elem else ''
                    side = side.lower().strip()

                    if side not in ('bullish', 'bearish'):
                        continue

                    # Parse option type (call/put)
                    option_elem = await row.query_selector('[data-option-type], .option-type, td:nth-child(4)')
                    option_type = await option_elem.inner_text() if option_elem else ''
                    option_type = option_type.lower().strip()

                    if option_type not in ('call', 'put'):
                        continue

                    # Parse premium
                    premium_elem = await row.query_selector('[data-premium], .premium, td:nth-child(5)')
                    premium_text = await premium_elem.inner_text() if premium_elem else '0'
                    premium = self._parse_premium(premium_text)

                    if premium < MIN_PREMIUM:
                        continue

                    # Parse strike
                    strike_elem = await row.query_selector('[data-strike], .strike, td:nth-child(6)')
                    strike_text = await strike_elem.inner_text() if strike_elem else '0'
                    strike = float(strike_text.replace('$', '').replace(',', '').strip())

                    # Parse expiry
                    expiry_elem = await row.query_selector('[data-expiry], .expiry, td:nth-child(7)')
                    expiry = await expiry_elem.inner_text() if expiry_elem else ''

                    # Create entry
                    entry = FlowEntry(
                        timestamp=datetime.utcnow(),  # Use UTC for Docker compatibility
                        ticker=ticker.strip(),
                        flow_type=flow_type,
                        side=side,
                        option_type=option_type,
                        premium=premium,
                        strike=strike,
                        expiry=expiry.strip(),
                        raw_data={}
                    )

                    entries.append(entry)

                except Exception as row_err:
                    logger.debug(f"Failed to parse row: {row_err}")
                    continue

            logger.info(f"Parsed {len(entries)} qualifying flow entries")
            return entries

        except Exception as e:
            logger.error(f"Failed to parse flow table: {e}", exc_info=True)
            return []

    @staticmethod
    def _parse_premium(text: str) -> float:
        """Parse premium from text like '$50.2K' or '$1.2M'"""
        try:
            text = text.strip().upper().replace('$', '').replace(',', '')

            if 'K' in text:
                return float(text.replace('K', '')) * 1000
            elif 'M' in text:
                return float(text.replace('M', '')) * 1000000
            else:
                return float(text)
        except:
            return 0.0

    async def close(self):
        """Close browser"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")


# Global scraper instance
scraper: Optional[FlowAlgoScraper] = None


async def polling_loop():
    """Main polling loop that scrapes FlowAlgo periodically"""
    global scraper

    logger.info("Starting polling loop...")

    try:
        scraper = FlowAlgoScraper()
        await scraper.initialize()

        while True:
            try:
                # Scrape latest flows
                entries = await scraper.scrape_dashboard()

                # Add to store
                for entry in entries:
                    flow_store.add_entry(entry)

                # Random delay between polls
                delay = random.randint(POLL_INTERVAL_MIN, POLL_INTERVAL_MAX)
                logger.info(f"Next scrape in {delay}s...")
                await asyncio.sleep(delay)

                # Additional random delay to avoid patterns
                await asyncio.sleep(random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX))

            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    except Exception as e:
        logger.error(f"Fatal error in polling loop: {e}", exc_info=True)
        if scraper:
            await scraper.close()


def start_polling_thread():
    """Start the async polling loop in a background thread"""
    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(polling_loop())

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    logger.info("Polling thread started")


# Flask routes

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'logged_in': scraper.logged_in if scraper else False,
        'last_scrape': scraper.last_scrape.isoformat() if scraper and scraper.last_scrape else None,
        'flow_entries': len(flow_store.entries)
    })


@app.route('/filter', methods=['POST'])
def filter_webhook():
    """
    Filter TradingView webhook through flow confluence check.

    Request body:
    {
        "ticker": "MES",
        "action": "buy",
        "price": 5500,
        ...other fields
    }
    """
    try:
        payload = request.get_json()

        if not payload:
            return jsonify({'error': 'Invalid JSON'}), 400

        tv_ticker = payload.get('ticker', '').upper()
        tv_action = payload.get('action', '').lower()

        logger.info(f"Received TV webhook: {tv_ticker} {tv_action}")

        # Map ticker
        proxy_ticker = TICKER_MAP.get(tv_ticker, tv_ticker)

        if proxy_ticker not in ALL_TRACKED_TICKERS:
            logger.info(f"Ticker {tv_ticker} (mapped: {proxy_ticker}) not in target list, skipping")
            return jsonify({
                'status': 'skipped',
                'reason': f'ticker {proxy_ticker} not tracked'
            }), 200

        # Check confluence
        matching_flow = flow_store.check_confluence(
            ticker=proxy_ticker,
            tv_action=tv_action,
            minutes=CONFLUENCE_WINDOW_MINUTES
        )

        if not matching_flow:
            logger.info(f"No confluence for {proxy_ticker} {tv_action}, NOT forwarding")
            return jsonify({
                'status': 'skipped',
                'reason': 'no flow confluence',
                'checked_ticker': proxy_ticker,
                'tv_action': tv_action
            }), 200

        # Confluence found - forward to mytradeflow.app
        logger.info(f"Confluence detected! Forwarding to {MYTRADEFLOW_WEBHOOK}")

        import requests
        response = requests.post(
            MYTRADEFLOW_WEBHOOK,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        logger.info(f"Forwarded to mytradeflow.app: {response.status_code}")

        return jsonify({
            'status': 'forwarded',
            'confluence': {
                'ticker': matching_flow.ticker,
                'side': matching_flow.side,
                'type': matching_flow.option_type,
                'premium': matching_flow.premium,
                'flow_type': matching_flow.flow_type
            },
            'mytradeflow_response': response.status_code
        }), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/recent', methods=['GET'])
def get_recent_flow():
    """Get recent flow entries (for debugging)"""
    ticker = request.args.get('ticker', '').upper()
    minutes = int(request.args.get('minutes', '5'))

    if ticker:
        entries = flow_store.get_recent_entries(ticker, minutes)
    else:
        cutoff = datetime.now() - timedelta(minutes=minutes)
        with flow_store.lock:
            entries = [e for e in flow_store.entries if e.timestamp >= cutoff]

    return jsonify({
        'count': len(entries),
        'entries': [
            {
                'ticker': e.ticker,
                'side': e.side,
                'type': e.option_type,
                'flow_type': e.flow_type,
                'premium': e.premium,
                'strike': e.strike,
                'timestamp': e.timestamp.isoformat()
            }
            for e in entries
        ]
    })


def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("FlowAlgo Confluence Webhook Proxy Starting...")
    logger.info("=" * 80)
    logger.info(f"Flask server: http://0.0.0.0:{FLASK_PORT}")
    logger.info(f"Target webhook: {MYTRADEFLOW_WEBHOOK}")
    logger.info(f"Tracking tickers: {', '.join(ALL_TRACKED_TICKERS)}")
    logger.info(f"Confluence window: {CONFLUENCE_WINDOW_MINUTES} minutes")
    logger.info(f"Min premium: ${MIN_PREMIUM:,}")
    logger.info("=" * 80)

    # Start polling thread
    start_polling_thread()

    # Give scraper time to initialize
    time.sleep(5)

    # Start Flask server
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=False, threaded=True)


if __name__ == '__main__':
    main()
