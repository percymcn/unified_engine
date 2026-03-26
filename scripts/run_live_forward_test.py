#!/usr/bin/env python3
"""
Live Forward Test Runner - SmartFlow DYNAMIC Strategy
======================================================

Automatically adjusts between trending (2%/2%) and ranging (1%/1%) stops
based on real-time market regime detection.

NOW WITH WEBHOOK SIGNAL GENERATION - Sends signals to live broker accounts!

Usage:
    python scripts/run_live_forward_test.py                      # Default tickers
    python scripts/run_live_forward_test.py --tickers US30 NAS100 # Indices
    python scripts/run_live_forward_test.py --dynamic             # Enable dynamic adjustment
    python scripts/run_live_forward_test.py --daemon              # Run as background service
    python scripts/run_live_forward_test.py --webhook             # Send signals to webhook
    python scripts/run_live_forward_test.py --webhook-key KEY     # Specify webhook key

Data Sources:
    - Kraken: Crypto (BTCUSD, ETHUSD) - 24/7 trading
    - ProjectX SDK: Real-time futures (MES, MNQ, MYM)
    - Polygon: CFD proxies (SPY->MES, QQQ->MNQ, DIA->MYM)
    - Polygon Forex: USDJPY, GBPJPY for MT5/TradeLocker
"""

import asyncio
import sys
import os
import argparse
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import signal

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('LiveForwardTest')

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import services
from app.services.forward_test import ForwardTester, ForwardTestConfig

# Import Unified Flow Feature Engine for enhanced flow scoring
try:
    from app.services.flow_feature_engine import UnifiedFlowFeatureEngine, FlowFeatureBundle
    FLOW_ENGINE_AVAILABLE = True
except ImportError:
    FLOW_ENGINE_AVAILABLE = False
    UnifiedFlowFeatureEngine = None
    FlowFeatureBundle = None

# ===========================================================================
# PHASE 4 ALIGNMENT: Full SmartFlow Architecture Integration
# ===========================================================================
# Feature flag to enable full architecture (router → registry → engine → guard)
# Set to True to use aligned path, False for legacy fallback
USE_FULL_ARCHITECTURE = os.getenv('SMARTFLOW_FULL_ARCHITECTURE', 'true').lower() == 'true'

# Import Adaptive Router
try:
    from app.services.smartflow_engine_router import (
        SmartFlowEngineRouter, get_router, RouterDecision, RoutingMode
    )
    ROUTER_AVAILABLE = True
except ImportError as e:
    ROUTER_AVAILABLE = False
    logger.warning(f"SmartFlow Router not available: {e}")

# Import Agentic Monitor for autonomous trade validation
try:
    from app.services.agentic_monitor import (
        get_agentic_monitor, validate_before_trade, AgenticMonitor
    )
    MONITOR_AVAILABLE = True
except ImportError as e:
    MONITOR_AVAILABLE = False
    logger.warning(f"Agentic Monitor not available: {e}")

# Import AI Trading Supervisor for intelligent monitoring
try:
    from app.services.ai_trading_supervisor import (
        get_ai_supervisor, AITradingSupervisor
    )
    AI_SUPERVISOR_AVAILABLE = True
except ImportError as e:
    AI_SUPERVISOR_AVAILABLE = False
    logger.warning(f"AI Trading Supervisor not available: {e}")

# Import Strategy Engines
try:
    from app.services.strategy_engines.base import SignalContext, TradingSignal
    from app.services.strategy_engines.breakout import BreakoutEngine
    from app.services.strategy_engines.trend import TrendEngine
    from app.services.strategy_engines.mean_reversion import MeanReversionEngine
    from app.services.strategy_engines.liquidity_reversal import LiquidityReversalEngine
    STRATEGY_ENGINES_AVAILABLE = True
    STRATEGY_ENGINES = {
        'breakout': BreakoutEngine,
        'trend': TrendEngine,
        'mean_reversion': MeanReversionEngine,
        'liquidity_reversal': LiquidityReversalEngine,
        # Fallback to unified scoring for these
        'unified': None,
        'deterministic': None,
        'quick': None,
    }
except ImportError as e:
    STRATEGY_ENGINES_AVAILABLE = False
    STRATEGY_ENGINES = {}
    logger.warning(f"Strategy engines not available: {e}")

# Import Signal Intelligence Guard and DB session support
try:
    from app.services.signal_intelligence_guard import (
        SignalIntelligenceGuard,
        GuardDecision,
        GuardResult
    )
    from app.core.database import SessionLocal
    from app.domain.entities.signal import Signal
    from app.domain.value_objects import SignalId, Symbol, Volume, Price
    from app.domain.enums import SignalSource, SignalAction
    from decimal import Decimal
    import uuid
    SIGNAL_GUARD_AVAILABLE = True

    # Forward test uses synthetic user ID for guard settings
    # User 'forward_test@system.local' created in DB with id=1
    FORWARD_TEST_USER_ID = 1
except ImportError as e:
    SIGNAL_GUARD_AVAILABLE = False
    logger.warning(f"Signal Intelligence Guard not available: {e}")

# Import Allocator (metadata-first)
try:
    from app.services.strategy_allocator import StrategyAllocator
    ALLOCATOR_AVAILABLE = True
except ImportError as e:
    ALLOCATOR_AVAILABLE = False
    logger.warning(f"Strategy Allocator not available: {e}")

# Import Signal Agreement Layer (Quick Anchor + Regime Adaptive Enhancer)
try:
    from app.services.signal_agreement import (
        SignalAgreementLayer,
        AnchorSignal,
        RegimeSignal,
        AgreementResult,
        AgreementState,
        FinalDecision,
        evaluate_signal_agreement,
        get_signal_agreement_layer,
    )
    SIGNAL_AGREEMENT_AVAILABLE = True
except ImportError as e:
    SIGNAL_AGREEMENT_AVAILABLE = False
    logger.warning(f"Signal Agreement Layer not available: {e}")

# Import AI Feature Engine (metadata-first)
try:
    from app.services.ai_feature_engine import AIFeatureEngine, get_ai_feature_engine
    AI_ENGINE_AVAILABLE = True
except ImportError as e:
    AI_ENGINE_AVAILABLE = False
    logger.warning(f"AI Feature Engine not available: {e}")

# Import Advanced Risk Manager (metadata-first)
try:
    from app.services.advanced_risk import AdvancedRiskManager, get_advanced_risk_manager
    RISK_ENGINE_AVAILABLE = True
except ImportError as e:
    RISK_ENGINE_AVAILABLE = False
    logger.warning(f"Advanced Risk Manager not available: {e}")

# Import Portfolio Risk Engine (metadata-first + optional blocking)
try:
    from app.services.strategy_registry.portfolio_risk import (
        PortfolioRiskEngine, get_portfolio_risk_engine, PortfolioRiskSnapshot
    )
    PORTFOLIO_RISK_AVAILABLE = True
except ImportError as e:
    PORTFOLIO_RISK_AVAILABLE = False
    logger.warning(f"Portfolio Risk Engine not available: {e}")

# Import Execution Quality Tracker (metadata-first)
try:
    from app.services.strategy_registry.execution_quality import (
        ExecutionQualityTracker, get_execution_tracker, StrategyExecutionQuality
    )
    EXECUTION_QUALITY_AVAILABLE = True
except ImportError as e:
    EXECUTION_QUALITY_AVAILABLE = False
    logger.warning(f"Execution Quality Tracker not available: {e}")

# ===========================================================================

# Timezone import for EST
from zoneinfo import ZoneInfo
EST_TZ = ZoneInfo("America/New_York")


class BrokerPositionSync:
    """
    Syncs broker positions with internal forward test state.

    Checks actual broker positions to:
    - Detect manually closed positions
    - Detect SL/TP hits
    - Allow new signals when positions are closed
    """

    def __init__(self):
        self.projectx_service = None
        self._last_sync: datetime = None
        self._sync_interval = 60  # Sync every 60 seconds
        self._broker_positions: Dict[str, Dict] = {}  # ticker -> position info
        self._position_count_cache: Dict[str, int] = {}  # ticker -> count

    async def initialize(self) -> bool:
        """Initialize connection to ProjectX for position sync."""
        try:
            from app.services.projectx_sdk_service import ProjectXSDKService

            # Read credentials
            username = self._read_secret("projectx_username", "PROJECTX_USERNAME")
            api_key = self._read_secret("projectx_api_key", "PROJECTX_API_KEY")

            if username and api_key:
                self.projectx_service = ProjectXSDKService(
                    username=username,
                    api_key=api_key
                )
                connected = await self.projectx_service.connect()
                if connected:
                    logger.info("[POSITION SYNC] Connected to ProjectX for position sync")
                    return True
                else:
                    logger.warning("[POSITION SYNC] Failed to connect to ProjectX")
        except Exception as e:
            logger.warning(f"[POSITION SYNC] ProjectX not available for position sync: {e}")

        return False

    def _read_secret(self, secret_name: str, env_var: str = None) -> str:
        """Read from Docker secret or environment variable."""
        secret_path = f"/run/secrets/{secret_name}"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        if env_var:
            return os.getenv(env_var, "")
        return ""

    async def sync_positions(self) -> Dict[str, Any]:
        """
        Sync with broker to get actual position state.

        Returns:
            Dict with position changes detected
        """
        if not self.projectx_service:
            return {"synced": False, "reason": "no_connection"}

        # Rate limit syncs
        now = datetime.now(EST_TZ)
        if self._last_sync:
            elapsed = (now - self._last_sync).total_seconds()
            if elapsed < self._sync_interval:
                return {"synced": False, "reason": "rate_limited", "next_sync_in": self._sync_interval - elapsed}

        self._last_sync = now

        try:
            positions = await self.projectx_service.get_positions()
            logger.info(f"[POSITION SYNC] Fetched {len(positions)} positions from broker")

            # Build new position map
            new_positions: Dict[str, Dict] = {}
            position_counts: Dict[str, int] = {}

            for pos in positions:
                symbol = pos.get('symbol', '').upper()
                # Normalize symbol to ticker format
                ticker = self._normalize_to_ticker(symbol)
                if ticker:
                    new_positions[ticker] = pos
                    position_counts[ticker] = position_counts.get(ticker, 0) + 1

            # Detect changes
            closed_positions = []
            new_positions_list = []

            # Check for closed positions (was open, now not)
            for ticker, old_pos in self._broker_positions.items():
                if ticker not in new_positions:
                    closed_positions.append({
                        "ticker": ticker,
                        "side": old_pos.get('side', 'unknown'),
                        "size": old_pos.get('size', 0),
                        "pnl": old_pos.get('pnl', 0),
                    })
                    logger.info(f"[POSITION SYNC] Detected closed position: {ticker}")

            # Check for new positions
            for ticker, new_pos in new_positions.items():
                if ticker not in self._broker_positions:
                    new_positions_list.append({
                        "ticker": ticker,
                        "side": new_pos.get('side', 'unknown'),
                        "size": new_pos.get('size', 0),
                    })
                    logger.info(f"[POSITION SYNC] Detected new position: {ticker}")

            # Update cache
            self._broker_positions = new_positions
            self._position_count_cache = position_counts

            return {
                "synced": True,
                "timestamp": now.isoformat(),
                "total_positions": len(positions),
                "closed_positions": closed_positions,
                "new_positions": new_positions_list,
            }

        except Exception as e:
            logger.error(f"[POSITION SYNC] Failed to sync positions: {e}")
            return {"synced": False, "reason": str(e)}

    def _normalize_to_ticker(self, symbol: str) -> Optional[str]:
        """Normalize broker symbol to our ticker format."""
        # Map futures symbols to CFD tickers
        symbol_map = {
            'MYM': 'US30', 'YM': 'US30',
            'MNQ': 'NAS100', 'NQ': 'NAS100',
            'MES': 'SPX500', 'ES': 'SPX500',
            'MGC': 'XAUUSD', 'GC': 'XAUUSD',
        }

        # Strip contract month codes (e.g., MESH26 -> MES)
        import re
        base = re.sub(r'[FGHJKMNQUVXZ]\d{1,4}$', '', symbol.upper())

        return symbol_map.get(base, base if base else None)

    def get_broker_position_count(self, ticker: str) -> int:
        """Get number of broker positions for a ticker."""
        # Normalize ticker
        ticker_upper = ticker.upper()
        return self._position_count_cache.get(ticker_upper, 0)

    def has_broker_position(self, ticker: str) -> bool:
        """Check if broker has open position for ticker."""
        return self.get_broker_position_count(ticker) > 0

    def get_available_slots(self, ticker: str, max_positions: int = 3) -> int:
        """Get available position slots (max - current)."""
        current = self.get_broker_position_count(ticker)
        return max(0, max_positions - current)


class WebhookSignalSender:
    """
    Sends trading signals to the webhook endpoint for live broker execution.

    Supports three modes:
    1. Internal API: Uses webhook_key with /api/v1/webhook/execute
    2. External URL: Direct POST to full webhook URL (TradingView-style)
    3. Direct ProjectX: Places bracket orders directly on ProjectX with SL/TP
    """

    def __init__(self, webhook_key: str = None, base_url: str = None, webhook_url: str = None):
        # Check for direct webhook URL first (external mode)
        self.webhook_url = webhook_url or os.getenv('SMARTFLOW_WEBHOOK_URL', '')
        self.external_mode = bool(self.webhook_url)

        # Direct ProjectX mode for bracket orders with SL/TP
        self.projectx_service = None
        self._projectx_enabled = False

        # Internal API mode
        self.webhook_key = webhook_key or os.getenv('SMARTFLOW_WEBHOOK_KEY', '')
        self.base_url = base_url or os.getenv('API_BASE_URL', 'http://localhost:8000')

        self.enabled = bool(self.webhook_url) or bool(self.webhook_key)
        self._session = None

        # Signal tracking
        self.signals_sent = 0
        self.signals_failed = 0
        self.last_error = None
        self.signal_log: List[Dict] = []
        self.signal_log_file = "/app/data/signal_log.json"

        # Signal cooldown to prevent spamming (5 minutes per ticker)
        self._last_signal_time: Dict[str, datetime] = {}
        self._cooldown_seconds = 300  # 5 minutes
        self._signals_skipped = 0

        if self.external_mode:
            logger.info(f"WebhookSignalSender enabled with external URL: {self.webhook_url[:50]}...")
        elif self.webhook_key:
            logger.info(f"WebhookSignalSender enabled with key: {self.webhook_key[:8]}...")
        else:
            logger.info("WebhookSignalSender disabled (no webhook configured)")

    async def initialize_projectx_direct(self) -> bool:
        """Initialize direct ProjectX connection for bracket orders with SL/TP."""
        try:
            from app.services.projectx_sdk_service import ProjectXSDKService

            # Read credentials from Docker secrets or env vars
            username = self._read_secret("projectx_username", "PROJECTX_USERNAME")
            api_key = self._read_secret("projectx_api_key", "PROJECTX_API_KEY")

            if username and api_key:
                self.projectx_service = ProjectXSDKService(
                    username=username,
                    api_key=api_key
                )
                connected = await self.projectx_service.connect()
                if connected:
                    self._projectx_enabled = True
                    logger.info("[PROJECTX DIRECT] Connected - will use bracket orders for futures")
                    return True
                else:
                    logger.warning("[PROJECTX DIRECT] Connection failed")
        except Exception as e:
            logger.warning(f"[PROJECTX DIRECT] Not available: {e}")

        return False

    def _read_secret(self, secret_name: str, env_var: str = None) -> str:
        """Read from Docker secret or environment variable."""
        secret_path = f"/run/secrets/{secret_name}"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        if env_var:
            return os.getenv(env_var, "")
        return ""

    def _is_futures_ticker(self, ticker: str) -> bool:
        """Check if ticker is a futures instrument."""
        futures_tickers = ['US30', 'NAS100', 'SPX500', 'US500', 'XAUUSD', 'MES', 'MNQ', 'MYM', 'MGC']
        return ticker.upper() in futures_tickers

    def _map_to_futures_symbol(self, ticker: str) -> str:
        """Map CFD ticker to futures symbol."""
        ticker_map = {
            'US30': 'MYM', 'NAS100': 'MNQ', 'SPX500': 'MES',
            'US500': 'MES', 'XAUUSD': 'MGC'
        }
        return ticker_map.get(ticker.upper(), ticker)

    async def _get_session(self):
        """Get or create aiohttp session."""
        import aiohttp
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_signal(
        self,
        ticker: str,
        action: str,  # 'buy', 'sell', 'close'
        price: float,
        stop_loss: float = None,
        take_profit: float = None,
        quantity: float = None,
        comment: str = None,
        strategy_id: str = 'smartflow_forward_test'
    ) -> Dict[str, Any]:
        """
        Send a trading signal to the webhook endpoint.

        Args:
            ticker: Symbol to trade (e.g., 'USDJPY', 'US30')
            action: Trade action ('buy', 'sell', 'close')
            price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            quantity: Position size (default uses account sizing)
            comment: Trade comment
            strategy_id: Strategy identifier

        Returns:
            Dict with result info
        """
        if not self.enabled:
            return {'success': False, 'reason': 'webhook disabled'}

        # Check cooldown - prevent spamming same ticker
        ticker_key = ticker.upper()
        now = datetime.now(EST_TZ)
        last_signal = self._last_signal_time.get(ticker_key)

        if last_signal:
            elapsed = (now - last_signal).total_seconds()
            if elapsed < self._cooldown_seconds:
                remaining = self._cooldown_seconds - elapsed
                self._signals_skipped += 1
                logger.debug(f"[WEBHOOK] Cooldown: {ticker} signal skipped, {remaining:.0f}s remaining")
                return {
                    'success': False,
                    'reason': 'cooldown',
                    'cooldown_remaining': remaining,
                    'skipped_total': self._signals_skipped
                }

        # Update last signal time for this ticker
        self._last_signal_time[ticker_key] = now

        # Track results from both ProjectX and webhook
        results = {'success': False, 'projectx': None, 'webhook': None}

        # For futures tickers, place bracket order directly on ProjectX (with SL/TP)
        if self._projectx_enabled and self._is_futures_ticker(ticker) and action.lower() != 'close':
            try:
                futures_symbol = self._map_to_futures_symbol(ticker)
                side = 'buy' if action.lower() == 'buy' else 'sell'
                size = int(quantity) if quantity else 1  # Default to 1 contract

                logger.info(f"[PROJECTX DIRECT] Placing bracket order: {futures_symbol} {side} "
                           f"SL={stop_loss} TP={take_profit}")

                bracket_result = await self.projectx_service.place_bracket_order(
                    instrument=futures_symbol,
                    side=side,
                    size=size,
                    entry_price=None,  # Market order
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )

                if bracket_result.get('success'):
                    logger.info(f"[PROJECTX DIRECT] Bracket order placed successfully: {bracket_result}")
                    results['projectx'] = bracket_result
                    results['success'] = True
                else:
                    logger.warning(f"[PROJECTX DIRECT] Bracket order failed: {bracket_result}")
                    results['projectx'] = bracket_result

            except Exception as e:
                logger.error(f"[PROJECTX DIRECT] Bracket order error: {e}")
                results['projectx'] = {'error': str(e)}

        # Also send to webhook (for other brokers like MT5, TradeLocker)
        try:
            session = await self._get_session()

            # Build payload based on mode
            if self.external_mode:
                # TradingView-style payload for external webhooks
                payload = {
                    'action': action.lower(),
                    'symbol': ticker,
                    'price': price,
                    'timestamp': datetime.now(EST_TZ).isoformat(),
                    'strategy': strategy_id,
                    'message': comment or f'SmartFlow {action.upper()} {ticker} @ {price:.4f}'
                }
                if quantity:
                    payload['quantity'] = quantity
                if stop_loss:
                    payload['sl'] = stop_loss
                    payload['stoploss'] = stop_loss  # Some webhooks use this
                if take_profit:
                    payload['tp'] = take_profit
                    payload['takeprofit'] = take_profit  # Some webhooks use this
                url = self.webhook_url
            else:
                # Internal API payload
                payload = {
                    'webhook_key': self.webhook_key,
                    'action': action.lower(),
                    'symbol': ticker,
                    'timestamp': datetime.now(EST_TZ).isoformat(),
                    'strategy_id': strategy_id,
                    'comment': comment or f'SmartFlow signal @ {price:.4f}'
                }
                if quantity:
                    payload['quantity'] = quantity
                if stop_loss:
                    payload['sl'] = stop_loss
                if take_profit:
                    payload['tp'] = take_profit
                url = f"{self.base_url}/api/v1/webhook/execute"

            logger.info(f"[WEBHOOK] Sending {action.upper()} {ticker} @ {price:.4f} to {url[:50]}...")

            async with session.post(url, json=payload) as response:
                # Try to parse JSON, but handle non-JSON responses gracefully
                try:
                    result = await response.json()
                except Exception:
                    # Fix: await must be in parentheses before slicing
                    text = await response.text()
                    result = {'raw_response': text[:200]}

                if response.status in [200, 201, 202]:
                    self.signals_sent += 1
                    logger.info(f"[WEBHOOK] Signal sent successfully (status {response.status})")
                    # Log the signal for dashboard
                    self._log_signal(payload, status='sent')
                    results['webhook'] = {'success': True, 'result': result}
                    results['success'] = True
                else:
                    self.signals_failed += 1
                    self.last_error = f"HTTP {response.status}: {result.get('detail', result.get('raw_response', 'Unknown'))[:100]}"
                    logger.warning(f"[WEBHOOK] Signal failed: {self.last_error}")
                    # Log the failed signal
                    self._log_signal(payload, status='failed')
                    results['webhook'] = {'success': False, 'error': self.last_error}

        except Exception as e:
            self.signals_failed += 1
            error_msg = str(e) if str(e) else type(e).__name__
            self.last_error = error_msg
            logger.error(f"[WEBHOOK] Exception sending signal: {error_msg}")
            # Log the failed signal with full data including SL/TP
            signal_data = {
                'ticker': ticker, 'action': action, 'price': price,
                'stop_loss': stop_loss, 'take_profit': take_profit,
                'strategy': strategy_id
            }
            self._log_signal(signal_data, status='failed')
            results['webhook'] = {'success': False, 'error': error_msg}

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get webhook stats."""
        return {
            'enabled': self.enabled,
            'signals_sent': self.signals_sent,
            'signals_failed': self.signals_failed,
            'signals_skipped_cooldown': self._signals_skipped,
            'cooldown_seconds': self._cooldown_seconds,
            'last_error': self.last_error
        }

    def _log_signal(self, signal_data: Dict, status: str = 'pending'):
        """Log signal to memory and file for dashboard visibility."""
        import uuid

        signal_entry = {
            'id': str(uuid.uuid4())[:8],
            'ticker': signal_data.get('symbol', signal_data.get('ticker', 'UNKNOWN')),
            'action': signal_data.get('action', 'BUY').upper(),
            'price': signal_data.get('price', 0),
            'stop_loss': signal_data.get('sl') or signal_data.get('stop_loss'),
            'take_profit': signal_data.get('tp') or signal_data.get('take_profit'),
            'strategy': signal_data.get('strategy', 'SmartFlow'),
            'regime': signal_data.get('regime'),
            'probability': signal_data.get('probability'),
            'timestamp': datetime.now(EST_TZ).isoformat(),
            'webhook_status': status,
            'source': 'forward_test'
        }

        # Add to in-memory log (keep last 100)
        self.signal_log.append(signal_entry)
        if len(self.signal_log) > 100:
            self.signal_log = self.signal_log[-100:]

        # Write to file for API access
        try:
            os.makedirs(os.path.dirname(self.signal_log_file), exist_ok=True)
            with open(self.signal_log_file, 'w') as f:
                json.dump({
                    'signals': self.signal_log,
                    'stats': {
                        'total_sent': self.signals_sent,
                        'total_failed': self.signals_failed,
                        'last_update': datetime.now(EST_TZ).isoformat()
                    }
                }, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to write signal log: {e}")


@dataclass
class DynamicStrategyConfig:
    """Configuration for dynamic strategy adjustment."""
    # Trending market parameters (2%/2%) - for swing trades / non-futures
    trending_stop_pct: float = 2.0
    trending_target_pct: float = 2.0

    # Ranging market parameters (1%/1%)
    ranging_stop_pct: float = 1.0
    ranging_target_pct: float = 1.0

    # Volatile market parameters (1.5%/2.5%)
    volatile_stop_pct: float = 1.5
    volatile_target_pct: float = 2.5

    # Breakout parameters (2.5%/3%)
    breakout_stop_pct: float = 2.5
    breakout_target_pct: float = 3.0

    # ========================================
    # FUTURES DAY TRADING - TIGHT STOPS
    # ProjectX micro futures (MES, MNQ, MYM, MGC)
    # ========================================
    futures_stop_pct: float = 0.2   # 0.2% stop loss for day trading
    futures_target_pct: float = 0.4  # 0.4% take profit (2:1 R:R)

    # Futures regime adjustments (still tight but adjusted)
    futures_trending_stop_pct: float = 0.25  # Slightly wider for trending
    futures_trending_target_pct: float = 0.5
    futures_ranging_stop_pct: float = 0.15   # Tighter for ranging
    futures_ranging_target_pct: float = 0.3
    futures_volatile_stop_pct: float = 0.3   # Wider for volatile
    futures_volatile_target_pct: float = 0.4

    # Position sizing multipliers
    trending_size_mult: float = 1.0
    ranging_size_mult: float = 0.75  # Smaller size for mean-reversion
    volatile_size_mult: float = 0.5  # Smaller size for high volatility
    breakout_size_mult: float = 1.25  # Larger size for breakouts

    # Regime thresholds (24h % change)
    trending_threshold: float = 3.0  # >3% = trending
    ranging_threshold: float = 1.0   # <1% = ranging
    volatile_threshold: float = 5.0  # >5% = volatile

    # Performance tracking
    track_regime_performance: bool = True


class DynamicStrategyManager:
    """
    Dynamically adjusts strategy parameters based on market conditions.
    """

    def __init__(self, config: DynamicStrategyConfig = None):
        self.config = config or DynamicStrategyConfig()
        self._regime_history: Dict[str, List[str]] = {}
        self._regime_performance: Dict[str, Dict[str, Dict]] = {}
        self._current_regime: Dict[str, str] = {}
        self._volatility_cache: Dict[str, float] = {}
        self._last_adjustment: Dict[str, datetime] = {}

    def _is_futures_ticker(self, ticker: str) -> bool:
        """Check if ticker is a futures instrument requiring tight stops."""
        futures_tickers = ['US30', 'NAS100', 'SPX500', 'US500', 'XAUUSD', 'MES', 'MNQ', 'MYM', 'MGC']
        return ticker.upper() in futures_tickers

    def get_strategy_params(self, ticker: str, regime: str, volatility: float = None) -> Dict:
        """Get dynamic strategy parameters based on current conditions."""

        # Track regime history
        if ticker not in self._regime_history:
            self._regime_history[ticker] = []
        self._regime_history[ticker].append(regime)
        if len(self._regime_history[ticker]) > 100:
            self._regime_history[ticker] = self._regime_history[ticker][-50:]

        self._current_regime[ticker] = regime

        # Check if this is a futures ticker (day trading with tight stops)
        is_futures = self._is_futures_ticker(ticker)

        # Determine strategy based on regime
        if regime in ['trending_up', 'trending_down']:
            if is_futures:
                # Futures: 0.25% SL / 0.5% TP for trending
                params = {
                    'stop_pct': self.config.futures_trending_stop_pct,
                    'target_pct': self.config.futures_trending_target_pct,
                    'size_mult': self.config.trending_size_mult,
                    'strategy': 'FUTURES_TRENDING',
                    'mode': 'trend-following',
                }
            else:
                params = {
                    'stop_pct': self.config.trending_stop_pct,
                    'target_pct': self.config.trending_target_pct,
                    'size_mult': self.config.trending_size_mult,
                    'strategy': 'TRENDING',
                    'mode': 'trend-following',
                }
        elif regime == 'ranging':
            if is_futures:
                # Futures: 0.15% SL / 0.3% TP for ranging (tightest)
                params = {
                    'stop_pct': self.config.futures_ranging_stop_pct,
                    'target_pct': self.config.futures_ranging_target_pct,
                    'size_mult': self.config.ranging_size_mult,
                    'strategy': 'FUTURES_RANGING',
                    'mode': 'mean-reversion',
                }
            else:
                params = {
                    'stop_pct': self.config.ranging_stop_pct,
                    'target_pct': self.config.ranging_target_pct,
                    'size_mult': self.config.ranging_size_mult,
                    'strategy': 'RANGING',
                    'mode': 'mean-reversion',
                }
        elif regime == 'volatile':
            if is_futures:
                # Futures: 0.3% SL / 0.4% TP for volatile
                params = {
                    'stop_pct': self.config.futures_volatile_stop_pct,
                    'target_pct': self.config.futures_volatile_target_pct,
                    'size_mult': self.config.volatile_size_mult,
                    'strategy': 'FUTURES_VOLATILE',
                    'mode': 'reduced-exposure',
                }
            else:
                params = {
                    'stop_pct': self.config.volatile_stop_pct,
                    'target_pct': self.config.volatile_target_pct,
                    'size_mult': self.config.volatile_size_mult,
                    'strategy': 'VOLATILE',
                    'mode': 'reduced-exposure',
                }
        elif regime == 'breakout':
            if is_futures:
                # Futures breakout: 0.25% SL / 0.5% TP
                params = {
                    'stop_pct': self.config.futures_trending_stop_pct,
                    'target_pct': self.config.futures_trending_target_pct,
                    'size_mult': self.config.breakout_size_mult,
                    'strategy': 'FUTURES_BREAKOUT',
                    'mode': 'momentum',
                }
            else:
                params = {
                    'stop_pct': self.config.breakout_stop_pct,
                    'target_pct': self.config.breakout_target_pct,
                    'size_mult': self.config.breakout_size_mult,
                    'strategy': 'BREAKOUT',
                    'mode': 'momentum',
                }
        else:
            # Default - use base futures stops if futures ticker
            if is_futures:
                params = {
                    'stop_pct': self.config.futures_stop_pct,
                    'target_pct': self.config.futures_target_pct,
                    'size_mult': self.config.ranging_size_mult,
                    'strategy': 'FUTURES_DEFAULT',
                    'mode': 'conservative',
                }
            else:
                params = {
                    'stop_pct': self.config.ranging_stop_pct,
                    'target_pct': self.config.ranging_target_pct,
                    'size_mult': self.config.ranging_size_mult,
                    'strategy': 'DEFAULT',
                    'mode': 'conservative',
                }

        # Adjust for volatility if provided
        if volatility is not None:
            self._volatility_cache[ticker] = volatility
            if volatility > 5.0:  # High volatility
                params['size_mult'] *= 0.7
                params['stop_pct'] *= 1.2  # Wider stops
            elif volatility < 1.0:  # Low volatility
                params['size_mult'] *= 1.2
                params['stop_pct'] *= 0.9  # Tighter stops

        params['regime'] = regime
        return params

    def record_trade_result(self, ticker: str, regime: str, pnl: float, win: bool):
        """Record trade result for regime performance tracking."""
        if not self.config.track_regime_performance:
            return

        if ticker not in self._regime_performance:
            self._regime_performance[ticker] = {}
        if regime not in self._regime_performance[ticker]:
            self._regime_performance[ticker][regime] = {
                'trades': 0, 'wins': 0, 'total_pnl': 0.0
            }

        stats = self._regime_performance[ticker][regime]
        stats['trades'] += 1
        stats['wins'] += 1 if win else 0
        stats['total_pnl'] += pnl

    def get_regime_stats(self, ticker: str = None) -> Dict:
        """Get performance statistics by regime."""
        if ticker:
            return self._regime_performance.get(ticker, {})
        return self._regime_performance

    def get_current_regime(self, ticker: str) -> str:
        """Get current detected regime for ticker."""
        return self._current_regime.get(ticker, 'unknown')

    def get_regime_distribution(self, ticker: str) -> Dict[str, float]:
        """Get distribution of regimes from history."""
        if ticker not in self._regime_history:
            return {}

        history = self._regime_history[ticker]
        if not history:
            return {}

        counts = {}
        for regime in history:
            counts[regime] = counts.get(regime, 0) + 1

        total = len(history)
        return {k: v / total * 100 for k, v in counts.items()}


def print_banner(dynamic: bool = False):
    print("\n" + "=" * 70)
    print("  SMARTFLOW LIVE FORWARD TEST")
    if dynamic:
        print("  Strategy: DYNAMIC (Auto-adjusts to market conditions)")
    else:
        print("  Strategy: 2%/2% Pullback Pyramid (Sharpe 4.7+)")
    print("=" * 70)
    print("\nDynamic Strategy Modes:")
    print("  - TRENDING:  2%/2% stops, trend-following")
    print("  - RANGING:   1%/1% stops, mean-reversion")
    print("  - VOLATILE:  1.5%/2.5% stops, reduced exposure")
    print("  - BREAKOUT:  2.5%/3% stops, momentum")
    print("\nPyramid: BOTH directions, max 3 positions")
    print("Add-on: Pullback 50% + 2 bars continuation")
    print("=" * 70)


class LiveDataFeed:
    """
    Manages real-time data feeds from ProjectX and Polygon.
    """

    def __init__(self):
        self.projectx_service = None
        self.market_data_service = None
        self.regime_detector = None
        self.ensemble_scorer = None
        self.flow_feature_engine = None  # Unified flow engine
        self._initialized = False
        self._crypto_cache: Dict[str, Dict] = {}
        self._crypto_cache_time: Dict[str, datetime] = {}
        self._crypto_cache_ttl = 30  # Cache for 30 seconds

    def _read_secret(self, secret_name: str, env_var: str = None) -> str:
        """Read from Docker secret file or environment variable."""
        # Try Docker secret first
        secret_path = f"/run/secrets/{secret_name}"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"Failed to read secret {secret_name}: {e}")
        # Fallback to environment variable
        if env_var:
            return os.getenv(env_var, "")
        return ""

    async def initialize(self) -> bool:
        """Initialize data feed connections."""
        logger.info("Initializing data feed connections...")

        # Try to import and initialize services
        try:
            # ProjectX for futures - read from Docker secrets or env vars
            from app.services.projectx_sdk_service import ProjectXSDKService
            username = self._read_secret("projectx_username", "PROJECTX_USERNAME")
            api_key = self._read_secret("projectx_api_key", "PROJECTX_API_KEY")

            if username and api_key:
                logger.info(f"ProjectX credentials loaded (username: {username[:10]}...)")
                self.projectx_service = ProjectXSDKService(
                    username=username,
                    api_key=api_key
                )
                connected = await self.projectx_service.connect()
                if connected:
                    logger.info("ProjectX SDK connected - real-time futures data available")
                else:
                    logger.warning("ProjectX SDK connection failed")
                    self.projectx_service = None
            else:
                logger.info("ProjectX credentials not found - using fallback data sources")
        except Exception as e:
            logger.warning(f"ProjectX not available: {e}")

        try:
            # Market data service for indicators
            from app.services.market_data_service import MarketDataService
            self.market_data_service = MarketDataService(
                projectx_service=self.projectx_service
            )
            logger.info("Market Data Service initialized")
        except Exception as e:
            logger.warning(f"Market Data Service not available: {e}")

        try:
            # Regime detector
            from app.services.regime_detector import get_regime_detector
            self.regime_detector = get_regime_detector()
            logger.info("Regime Detector initialized")
        except Exception as e:
            logger.warning(f"Regime Detector not available: {e}")

        try:
            # Ensemble scorer
            from app.services.ensemble_scorer import get_ensemble_scorer
            self.ensemble_scorer = get_ensemble_scorer()
            logger.info("Ensemble Scorer initialized")
        except Exception as e:
            logger.warning(f"Ensemble Scorer not available: {e}")

        # Initialize Unified Flow Feature Engine
        try:
            if FLOW_ENGINE_AVAILABLE:
                self.flow_feature_engine = UnifiedFlowFeatureEngine()
                logger.info("Unified Flow Feature Engine initialized")
            else:
                logger.warning("Unified Flow Feature Engine not available - using legacy flow signals")
        except Exception as e:
            logger.warning(f"Unified Flow Feature Engine init failed: {e}")

        self._initialized = True
        return self.projectx_service is not None or self.market_data_service is not None

    async def get_ohlc(self, ticker: str) -> Optional[Dict]:
        """
        Get current OHLC bar for a ticker.

        Returns:
            {
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': int,
                'timestamp': datetime
            }
        """
        # Check if crypto ticker
        crypto_map = {
            'BTCUSD': 'X:BTCUSD',
            'ETHUSD': 'X:ETHUSD',
            'BTC': 'X:BTCUSD',
            'ETH': 'X:ETHUSD',
        }

        # Map CFD tickers to futures
        futures_map = {
            'US30': 'MYM',
            'NAS100': 'MNQ',
            'SPX500': 'MES',
            'US500': 'MES',
            'XAUUSD': 'MGC',  # Gold micro futures
        }

        # Forex pairs (for MT5/TradeLocker)
        forex_map = {
            'USDJPY': 'USDJPY',
            'GBPJPY': 'GBPJPY',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
        }

        # Handle crypto tickers via Polygon
        if ticker.upper() in crypto_map:
            polygon_ticker = crypto_map[ticker.upper()]
            return await self._get_polygon_crypto(polygon_ticker, ticker)

        # Handle forex pairs
        if ticker.upper() in forex_map:
            return await self._get_forex_data(ticker.upper())

        futures_ticker = futures_map.get(ticker, ticker)

        # Try ProjectX first (real-time futures)
        if self.projectx_service and futures_ticker in ['MES', 'MNQ', 'MYM', 'MGC']:
            try:
                bars = await self.projectx_service.get_market_data(
                    instrument=futures_ticker,
                    days=1,
                    interval=5  # 5-minute bars
                )
                if bars and len(bars) > 0:
                    last_bar = bars[-1]
                    return {
                        'open': float(last_bar.get('open', last_bar.get('Open', 0))),
                        'high': float(last_bar.get('high', last_bar.get('High', 0))),
                        'low': float(last_bar.get('low', last_bar.get('Low', 0))),
                        'close': float(last_bar.get('close', last_bar.get('Close', 0))),
                        'volume': int(last_bar.get('volume', last_bar.get('Volume', 0))),
                        'timestamp': datetime.now(),
                        'source': 'projectx',
                    }
            except Exception as e:
                logger.warning(f"ProjectX data failed for {futures_ticker}: {e}")

        # Fallback to Polygon (ETF proxies)
        if self.market_data_service:
            try:
                # Map futures to ETFs
                etf_map = {'MES': 'SPY', 'MNQ': 'QQQ', 'MYM': 'DIA', 'MGC': 'GLD'}
                etf_ticker = etf_map.get(futures_ticker, ticker)

                bars = self.market_data_service.get_bars(
                    ticker=etf_ticker,
                    timespan='minute',
                    multiplier=5,
                    limit=10
                )
                if bars and len(bars) > 0:
                    last_bar = bars[-1]
                    return {
                        'open': last_bar.open,
                        'high': last_bar.high,
                        'low': last_bar.low,
                        'close': last_bar.close,
                        'volume': last_bar.volume,
                        'timestamp': last_bar.timestamp,
                        'source': 'polygon',
                    }
            except Exception as e:
                logger.warning(f"Polygon data failed for {ticker}: {e}")

        return None

    async def _get_polygon_crypto(self, polygon_ticker: str, display_ticker: str) -> Optional[Dict]:
        """Get crypto OHLC from multiple sources with caching."""
        import requests

        # Check cache first
        cache_key = polygon_ticker
        if cache_key in self._crypto_cache:
            cache_time = self._crypto_cache_time.get(cache_key)
            if cache_time and (datetime.now() - cache_time).total_seconds() < self._crypto_cache_ttl:
                return self._crypto_cache[cache_key]

        # Try Kraken first (free, high rate limits, works globally)
        kraken_map = {
            'X:BTCUSD': 'XBTUSD',
            'X:ETHUSD': 'ETHUSD',
        }

        kraken_pair = kraken_map.get(polygon_ticker)
        if kraken_pair:
            try:
                # Get OHLC data
                url = f"https://api.kraken.com/0/public/OHLC"
                params = {'pair': kraken_pair, 'interval': 5}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get('result'):
                    # Get the pair data (key varies)
                    pair_key = list(data['result'].keys())[0]
                    if pair_key != 'last':
                        ohlc_data = data['result'][pair_key]
                        if ohlc_data and len(ohlc_data) > 0:
                            bar = ohlc_data[-1]  # Most recent
                            result = {
                                'open': float(bar[1]),
                                'high': float(bar[2]),
                                'low': float(bar[3]),
                                'close': float(bar[4]),
                                'volume': float(bar[6]),
                                'timestamp': datetime.fromtimestamp(bar[0]),
                                'source': 'kraken',
                            }
                            # Cache result
                            self._crypto_cache[cache_key] = result
                            self._crypto_cache_time[cache_key] = datetime.now()
                            return result
            except Exception as e:
                logger.debug(f"Kraken failed for {display_ticker}: {e}")

        # Fallback to CoinGecko
        coingecko_map = {
            'X:BTCUSD': 'bitcoin',
            'X:ETHUSD': 'ethereum',
        }

        coin_id = coingecko_map.get(polygon_ticker)
        if coin_id:
            try:
                url = f"https://api.coingecko.com/api/v3/simple/price"
                params = {
                    'ids': coin_id,
                    'vs_currencies': 'usd',
                    'include_24hr_high': 'true',
                    'include_24hr_low': 'true',
                    'include_24hr_change': 'true',
                }
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if coin_id in data:
                    price_data = data[coin_id]
                    price = price_data['usd']
                    high = price_data.get('usd_24h_high', price * 1.01)
                    low = price_data.get('usd_24h_low', price * 0.99)

                    result = {
                        'open': price,  # Approximate
                        'high': high,
                        'low': low,
                        'close': price,
                        'volume': 0,
                        'timestamp': datetime.now(),
                        'source': 'coingecko',
                    }
                    # Cache result
                    self._crypto_cache[cache_key] = result
                    self._crypto_cache_time[cache_key] = datetime.now()
                    return result
            except Exception as e:
                logger.debug(f"CoinGecko failed for {display_ticker}: {e}")

        # Fallback to Polygon if available
        api_key = os.getenv('POLYGON_API_KEY', '')
        if api_key:
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{polygon_ticker}/prev"
                params = {'apiKey': api_key}

                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get('status') in ['OK', 'DELAYED'] and data.get('results'):
                    bar = data['results'][0]
                    result = {
                        'open': bar['o'],
                        'high': bar['h'],
                        'low': bar['l'],
                        'close': bar['c'],
                        'volume': int(bar['v']),
                        'timestamp': datetime.fromtimestamp(bar['t'] / 1000),
                        'source': 'polygon_crypto',
                    }
                    # Cache result
                    self._crypto_cache[cache_key] = result
                    self._crypto_cache_time[cache_key] = datetime.now()
                    return result
            except Exception as e:
                logger.debug(f"Polygon crypto failed for {display_ticker}: {e}")

        # Return cached data if available (even if stale)
        if cache_key in self._crypto_cache:
            logger.debug(f"Using stale cache for {display_ticker}")
            return self._crypto_cache[cache_key]

        return None

    async def _get_forex_data(self, ticker: str) -> Optional[Dict]:
        """Get forex OHLC data from Polygon or fallback sources."""
        import requests

        # Cache check
        cache_key = f"forex_{ticker}"
        if cache_key in self._crypto_cache:
            cache_time = self._crypto_cache_time.get(cache_key)
            if cache_time and (datetime.now() - cache_time).total_seconds() < self._crypto_cache_ttl:
                return self._crypto_cache[cache_key]

        # Try Polygon forex API
        api_key = os.getenv('POLYGON_API_KEY', '')
        if api_key:
            try:
                # Polygon forex ticker format: C:USDJPY
                polygon_ticker = f"C:{ticker}"
                url = f"https://api.polygon.io/v2/aggs/ticker/{polygon_ticker}/prev"
                params = {'apiKey': api_key}

                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get('status') in ['OK', 'DELAYED'] and data.get('results'):
                    bar = data['results'][0]
                    result = {
                        'open': bar['o'],
                        'high': bar['h'],
                        'low': bar['l'],
                        'close': bar['c'],
                        'volume': int(bar.get('v', 0)),
                        'timestamp': datetime.fromtimestamp(bar['t'] / 1000),
                        'source': 'polygon_forex',
                    }
                    self._crypto_cache[cache_key] = result
                    self._crypto_cache_time[cache_key] = datetime.now()
                    return result
            except Exception as e:
                logger.debug(f"Polygon forex failed for {ticker}: {e}")

        # Fallback: Use exchangerate-api or Alpha Vantage
        try:
            # Simple rate lookup for forex
            url = f"https://api.exchangerate.host/latest?base={ticker[:3]}&symbols={ticker[3:]}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('success') and data.get('rates'):
                rate = data['rates'].get(ticker[3:], 0)
                if rate:
                    result = {
                        'open': rate,
                        'high': rate * 1.001,
                        'low': rate * 0.999,
                        'close': rate,
                        'volume': 0,
                        'timestamp': datetime.now(),
                        'source': 'exchangerate',
                    }
                    self._crypto_cache[cache_key] = result
                    self._crypto_cache_time[cache_key] = datetime.now()
                    return result
        except Exception as e:
            logger.debug(f"Exchange rate fallback failed for {ticker}: {e}")

        # Return cached if available
        if cache_key in self._crypto_cache:
            return self._crypto_cache[cache_key]

        return None

    async def _get_crypto_regime(self, ticker: str) -> str:
        """Get simplified regime for crypto based on price change."""
        import requests

        # Use Kraken ticker stats
        kraken_map = {
            'BTCUSD': 'XBTUSD', 'BTC': 'XBTUSD',
            'ETHUSD': 'ETHUSD', 'ETH': 'ETHUSD',
        }
        kraken_pair = kraken_map.get(ticker.upper())

        if kraken_pair:
            try:
                url = f"https://api.kraken.com/0/public/Ticker"
                params = {'pair': kraken_pair}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get('result'):
                    pair_key = list(data['result'].keys())[0]
                    ticker_data = data['result'][pair_key]

                    # Calculate 24h change from open and last price
                    open_price = float(ticker_data['o'])
                    last_price = float(ticker_data['c'][0])
                    change_24h = ((last_price - open_price) / open_price) * 100

                    # Simple regime based on 24h change
                    if change_24h > 3:
                        return 'trending_up'
                    elif change_24h < -3:
                        return 'trending_down'
                    elif abs(change_24h) > 1:
                        return 'breakout' if change_24h > 0 else 'ranging'
                    else:
                        return 'ranging'
            except Exception as e:
                logger.debug(f"Kraken regime failed for {ticker}: {e}")

        return 'ranging'

    async def _get_forex_regime(self, ticker: str) -> str:
        """Get simplified regime for forex based on price movement."""
        # Try to get forex data
        data = await self._get_forex_data(ticker)
        if data:
            try:
                # Calculate intraday range as volatility proxy
                high = data.get('high', data['close'])
                low = data.get('low', data['close'])
                close = data['close']

                if close > 0:
                    range_pct = ((high - low) / close) * 100

                    # Classify based on range
                    if range_pct > 0.5:
                        return 'volatile'
                    elif range_pct > 0.3:
                        return 'trending_up' if close > data.get('open', close) else 'trending_down'
                    elif range_pct > 0.15:
                        return 'breakout' if close > data.get('open', close) else 'ranging'
                    else:
                        return 'ranging'
            except Exception as e:
                logger.debug(f"Forex regime calculation failed for {ticker}: {e}")

        return 'ranging'

    async def _get_futures_regime(self, ticker: str) -> str:
        """Get regime for futures using ProjectX data directly."""
        futures_map = {
            'US30': 'MYM', 'NAS100': 'MNQ', 'SPX500': 'MES',
            'US500': 'MES', 'XAUUSD': 'MGC'
        }
        futures_ticker = futures_map.get(ticker.upper(), ticker)

        if not self.projectx_service:
            return 'ranging'

        try:
            bars = await self.projectx_service.get_market_data(
                instrument=futures_ticker,
                days=1,
                interval=5
            )

            if bars and len(bars) >= 10:
                # Calculate regime from bar data
                closes = [float(b.get('close', b.get('Close', 0))) for b in bars[-20:]]
                highs = [float(b.get('high', b.get('High', 0))) for b in bars[-20:]]
                lows = [float(b.get('low', b.get('Low', 0))) for b in bars[-20:]]

                if len(closes) >= 10 and closes[-1] > 0:
                    # Calculate price change
                    price_change = (closes[-1] - closes[0]) / closes[0] * 100

                    # Calculate average range (volatility)
                    avg_range = sum(h - l for h, l in zip(highs, lows)) / len(highs)
                    avg_range_pct = avg_range / closes[-1] * 100

                    # Calculate trend strength
                    higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
                    higher_lows = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
                    trend_score = (higher_highs + higher_lows) / (2 * (len(highs) - 1)) * 100

                    # Classify regime
                    if avg_range_pct > 1.5:
                        return 'volatile'
                    elif abs(price_change) > 0.5 and trend_score > 60:
                        return 'trending_up' if price_change > 0 else 'trending_down'
                    elif abs(price_change) > 0.3:
                        return 'breakout'
                    else:
                        return 'ranging'
        except Exception as e:
            logger.debug(f"ProjectX regime detection failed for {ticker}: {e}")

        return 'ranging'

    async def _get_futures_ensemble(self, ticker: str, direction: str) -> tuple:
        """Get ensemble score for futures using ProjectX data directly."""
        futures_map = {
            'US30': 'MYM', 'NAS100': 'MNQ', 'SPX500': 'MES',
            'US500': 'MES', 'XAUUSD': 'MGC'
        }
        futures_ticker = futures_map.get(ticker.upper(), ticker)

        if not self.projectx_service:
            return (0.55, 50.0)

        try:
            bars = await self.projectx_service.get_market_data(
                instrument=futures_ticker,
                days=1,
                interval=5
            )

            if bars and len(bars) >= 10:
                closes = [float(b.get('close', b.get('Close', 0))) for b in bars[-20:]]

                if len(closes) >= 10 and closes[-1] > 0:
                    # Calculate momentum
                    price_change = (closes[-1] - closes[0]) / closes[0] * 100

                    # Base confidence
                    confidence = 55.0

                    # Direction alignment bonus
                    if direction == 'long' and price_change > 0:
                        confidence += min(15, abs(price_change) * 10)
                    elif direction == 'short' and price_change < 0:
                        confidence += min(15, abs(price_change) * 10)
                    else:
                        confidence -= 5

                    # Momentum bonus
                    if abs(price_change) > 0.3:
                        confidence += 5

                    signal_strength = min(80, confidence * 1.1)
                    return (confidence / 100.0, signal_strength)

        except Exception as e:
            logger.debug(f"ProjectX ensemble failed for {ticker}: {e}")

        return (0.55, 50.0)

    async def get_regime(self, ticker: str) -> str:
        """Get current market regime for ticker."""
        # For crypto, use simplified regime based on 24h change
        if ticker.upper() in ['BTCUSD', 'ETHUSD', 'BTC', 'ETH']:
            return await self._get_crypto_regime(ticker)

        # For forex, use simplified regime based on volatility
        if ticker.upper() in ['USDJPY', 'GBPJPY', 'EURUSD', 'GBPUSD']:
            return await self._get_forex_regime(ticker)

        # For futures (indices, gold), use ProjectX data directly
        if ticker.upper() in ['US30', 'NAS100', 'SPX500', 'US500', 'XAUUSD']:
            return await self._get_futures_regime(ticker)

        if self.regime_detector and self.market_data_service:
            try:
                # Get bars for regime analysis
                etf_map = {'MES': 'SPY', 'MNQ': 'QQQ', 'MYM': 'DIA', 'MGC': 'GLD',
                          'US30': 'DIA', 'NAS100': 'QQQ', 'SPX500': 'SPY', 'US500': 'SPY',
                          'XAUUSD': 'GLD'}
                analysis_ticker = etf_map.get(ticker, ticker)

                bars = self.market_data_service.get_bars(
                    ticker=analysis_ticker,
                    timespan='minute',
                    multiplier=5,
                    limit=50
                )

                if bars and len(bars) >= 20:
                    import pandas as pd
                    df = pd.DataFrame([{
                        'open': b.open,
                        'high': b.high,
                        'low': b.low,
                        'close': b.close,
                        'volume': b.volume
                    } for b in bars])

                    analysis = self.regime_detector.detect_regime(df)
                    regime = analysis.regime.value

                    # Map to forward test regime names
                    regime_map = {
                        'trending': 'trending_up' if analysis.trend_direction == 'bullish' else 'trending_down',
                        'ranging': 'ranging',
                        'high_vol': 'volatile',
                        'low_vol': 'breakout',
                        'neutral': 'ranging'
                    }
                    return regime_map.get(regime, regime)

            except Exception as e:
                logger.debug(f"Regime detection failed for {ticker}: {e}")

        # Default to ranging (most conservative)
        return 'ranging'

    async def _get_crypto_ensemble(self, ticker: str, direction: str) -> tuple:
        """Get simplified ensemble score for crypto using Kraken."""
        import requests

        kraken_map = {
            'BTCUSD': 'XBTUSD', 'BTC': 'XBTUSD',
            'ETHUSD': 'ETHUSD', 'ETH': 'ETHUSD',
        }
        kraken_pair = kraken_map.get(ticker.upper())
        if not kraken_pair:
            return (0.55, 50.0)

        try:
            url = f"https://api.kraken.com/0/public/Ticker"
            params = {'pair': kraken_pair}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('result'):
                pair_key = list(data['result'].keys())[0]
                ticker_data = data['result'][pair_key]

                open_price = float(ticker_data['o'])
                last_price = float(ticker_data['c'][0])
                change_24h = ((last_price - open_price) / open_price) * 100

                # Base confidence
                confidence = 55.0

                # Direction alignment bonus
                if direction == 'long' and change_24h > 0:
                    confidence += min(15, abs(change_24h) * 3)
                elif direction == 'short' and change_24h < 0:
                    confidence += min(15, abs(change_24h) * 3)
                else:
                    confidence -= 5  # Counter-trend penalty

                # Momentum bonus for strong moves
                if abs(change_24h) > 2:
                    confidence += 5

                signal_strength = min(80, confidence * 1.1)
                return (confidence / 100.0, signal_strength)

        except Exception as e:
            logger.debug(f"Crypto ensemble failed for {ticker}: {e}")

        return (0.55, 50.0)

    async def _get_forex_ensemble(self, ticker: str, direction: str) -> tuple:
        """Get simplified ensemble score for forex based on price data."""
        data = await self._get_forex_data(ticker)
        if data:
            try:
                open_price = data.get('open', data['close'])
                close = data['close']
                high = data.get('high', close)
                low = data.get('low', close)

                # Calculate intraday change
                if open_price > 0:
                    change_pct = ((close - open_price) / open_price) * 100
                else:
                    change_pct = 0

                # Base confidence
                confidence = 55.0

                # Direction alignment bonus
                if direction == 'long' and change_pct > 0:
                    confidence += min(15, abs(change_pct) * 100)  # Forex moves are smaller (0.1% = 10 pips)
                elif direction == 'short' and change_pct < 0:
                    confidence += min(15, abs(change_pct) * 100)
                else:
                    confidence -= 5  # Counter-trend penalty

                # Range expansion bonus (volatility)
                if close > 0:
                    range_pct = ((high - low) / close) * 100
                    if range_pct > 0.3:
                        confidence += 5

                signal_strength = min(80, confidence * 1.1)
                return (confidence / 100.0, signal_strength)

            except Exception as e:
                logger.debug(f"Forex ensemble calculation failed for {ticker}: {e}")

        return (0.55, 50.0)

    async def _get_option_flow_signal(self, ticker: str, direction: str) -> Dict[str, Any]:
        """
        Get option flow signals from Polygon and Unusual Whales.

        Returns dict with:
            - flow_sentiment: 'bullish', 'bearish', 'neutral'
            - flow_confidence: 0-100
            - flow_details: dict with specific signals
        """
        result = {
            'flow_sentiment': 'neutral',
            'flow_confidence': 50.0,
            'flow_details': {},
            'polygon_active': False,
            'uw_active': False,
            'flowalgo_active': False,
        }

        # Map ticker to underlying for options
        ticker_to_underlying = {
            'US30': 'DIA', 'NAS100': 'QQQ', 'SPX500': 'SPY', 'US500': 'SPY',
            'XAUUSD': 'GLD', 'MYM': 'DIA', 'MNQ': 'QQQ', 'MES': 'SPY', 'MGC': 'GLD'
        }
        underlying = ticker_to_underlying.get(ticker.upper(), ticker.upper())

        bullish_signals = 0
        bearish_signals = 0
        total_premium_bullish = 0
        total_premium_bearish = 0

        # Try Polygon Options Flow
        try:
            from app.services.polygon_options_flow import get_polygon_flow_service
            polygon_service = get_polygon_flow_service()

            # Get recent option trades for the underlying
            trades = await polygon_service.fetch_options_trades(underlying, lookback_minutes=15)

            if trades:
                result['polygon_active'] = True
                for trade in trades:
                    premium = getattr(trade, 'premium', 0) or 0
                    opt_type = getattr(trade, 'option_type', '').lower()
                    sentiment = getattr(trade, 'sentiment', '').lower()

                    if sentiment == 'bullish' or (opt_type == 'call' and premium > 50000):
                        bullish_signals += 1
                        total_premium_bullish += premium
                    elif sentiment == 'bearish' or (opt_type == 'put' and premium > 50000):
                        bearish_signals += 1
                        total_premium_bearish += premium

                result['flow_details']['polygon_trades'] = len(trades)
                result['flow_details']['polygon_bullish'] = bullish_signals
                result['flow_details']['polygon_bearish'] = bearish_signals
                logger.info(f"[POLYGON FLOW] {underlying}: {len(trades)} trades, "
                           f"bull={bullish_signals}, bear={bearish_signals}")

        except Exception as e:
            logger.debug(f"Polygon options flow error for {underlying}: {e}")

        # Try Unusual Whales
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service
            uw_service = await get_unusual_whales_service()

            # Get flow summary for the underlying (returns FlowSummary object)
            flow_summary = await uw_service.get_flow_by_ticker(underlying, lookback_minutes=30)

            if flow_summary:
                result['uw_active'] = True

                # FlowSummary has: overall_sentiment, sentiment_score, net_premium, etc.
                uw_sentiment = flow_summary.overall_sentiment.value if hasattr(flow_summary.overall_sentiment, 'value') else str(flow_summary.overall_sentiment)
                uw_score = flow_summary.sentiment_score  # -100 to +100

                # Convert to bullish/bearish counts based on sentiment
                if uw_sentiment.lower() == 'bullish' or uw_score > 20:
                    bullish_signals += 2  # Weight UW higher
                    result['flow_details']['uw_sentiment'] = 'bullish'
                elif uw_sentiment.lower() == 'bearish' or uw_score < -20:
                    bearish_signals += 2
                    result['flow_details']['uw_sentiment'] = 'bearish'
                else:
                    result['flow_details']['uw_sentiment'] = 'neutral'

                result['flow_details']['uw_score'] = uw_score
                result['flow_details']['uw_net_premium'] = flow_summary.net_premium
                result['flow_details']['uw_large_trades'] = flow_summary.large_trades_count
                result['flow_details']['uw_whale_trades'] = flow_summary.whale_trades_count

                logger.info(f"[UW FLOW] {underlying}: sentiment={uw_sentiment}, "
                           f"score={uw_score:.0f}, net_premium=${flow_summary.net_premium/1e6:.1f}M, "
                           f"whales={flow_summary.whale_trades_count}")

        except Exception as e:
            logger.warning(f"Unusual Whales flow error for {underlying}: {e}")

        # Try FlowAlgo Proxy (local scraper service)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # FlowAlgo proxy runs on host - use host IP for Docker containers
                # Try host.docker.internal first (Docker Desktop), then host IP
                flowalgo_host = os.getenv("FLOWALGO_HOST", "192.168.1.254")
                url = f"http://{flowalgo_host}:9001/recent?ticker={underlying}&minutes=15"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        fa_data = await resp.json()
                        fa_entries = fa_data.get('entries', [])

                        if fa_entries:
                            result['flowalgo_active'] = True
                            fa_bullish = 0
                            fa_bearish = 0
                            fa_total_premium = 0

                            for entry in fa_entries:
                                side = entry.get('side', '').lower()
                                premium = entry.get('premium', 0) or 0
                                flow_type = entry.get('flow_type', '').lower()

                                # Weight sweeps higher than blocks
                                weight = 2 if flow_type == 'sweep' else 1

                                if side == 'bullish':
                                    fa_bullish += weight
                                    fa_total_premium += premium
                                elif side == 'bearish':
                                    fa_bearish += weight
                                    fa_total_premium += premium

                            # Add FlowAlgo signals (weight 3 - most reliable)
                            if fa_bullish > fa_bearish:
                                bullish_signals += 3
                                result['flow_details']['flowalgo_sentiment'] = 'bullish'
                            elif fa_bearish > fa_bullish:
                                bearish_signals += 3
                                result['flow_details']['flowalgo_sentiment'] = 'bearish'
                            else:
                                result['flow_details']['flowalgo_sentiment'] = 'neutral'

                            result['flow_details']['flowalgo_entries'] = len(fa_entries)
                            result['flow_details']['flowalgo_bullish'] = fa_bullish
                            result['flow_details']['flowalgo_bearish'] = fa_bearish
                            result['flow_details']['flowalgo_premium'] = fa_total_premium

                            logger.info(f"[FLOWALGO] {underlying}: {len(fa_entries)} flows, "
                                       f"bull={fa_bullish}, bear={fa_bearish}, "
                                       f"premium=${fa_total_premium/1e3:.0f}K")

        except Exception as e:
            logger.debug(f"FlowAlgo proxy error for {underlying}: {e}")

        # Calculate overall flow sentiment
        total_signals = bullish_signals + bearish_signals
        if total_signals > 0:
            bull_ratio = bullish_signals / total_signals
            if bull_ratio > 0.6:
                result['flow_sentiment'] = 'bullish'
                result['flow_confidence'] = min(90, 50 + (bull_ratio * 40))
            elif bull_ratio < 0.4:
                result['flow_sentiment'] = 'bearish'
                result['flow_confidence'] = min(90, 50 + ((1 - bull_ratio) * 40))
            else:
                result['flow_sentiment'] = 'neutral'
                result['flow_confidence'] = 50

            logger.info(f"[FLOW SIGNAL] {ticker}: {result['flow_sentiment']} "
                       f"({result['flow_confidence']:.0f}%) - "
                       f"bull={bullish_signals}, bear={bearish_signals}")

        return result

    async def get_ensemble_score(self, ticker: str, direction: str) -> tuple:
        """
        Get ensemble probability and signal strength.

        Returns:
            (ensemble_prob, signal_strength)
        """
        # For crypto, use simplified scoring based on price data
        if ticker.upper() in ['BTCUSD', 'ETHUSD', 'BTC', 'ETH']:
            return await self._get_crypto_ensemble(ticker, direction)

        # For forex, use simplified scoring based on price data
        if ticker.upper() in ['USDJPY', 'GBPJPY', 'EURUSD', 'GBPUSD']:
            return await self._get_forex_ensemble(ticker, direction)

        # For futures (indices, gold), use ProjectX data + option flow
        if ticker.upper() in ['US30', 'NAS100', 'SPX500', 'US500', 'XAUUSD']:
            # Get base score from ProjectX technicals
            base_prob, base_strength = await self._get_futures_ensemble(ticker, direction)

            # Use Unified Flow Feature Engine if available
            if self.flow_feature_engine:
                try:
                    # Get unified flow bundle (aggregates UW + FlowAlgo + Polygon)
                    flow_bundle = await self.flow_feature_engine.get_flow_feature_bundle(ticker)

                    # Calculate flow adjustment using strategy-specific weights
                    # Using "pyramid" strategy as default for forward test
                    flow_boost, flow_reason = self.flow_feature_engine.calculate_flow_adjustment(
                        flow_bundle,
                        direction=direction,
                        strategy_type="pyramid"
                    )
                    flow_sentiment = flow_bundle.flow_sentiment
                    flow_confidence = flow_bundle.flow_confidence * 100  # Convert to percentage

                    # Log detailed flow info
                    sources_active = [s for s, w in flow_bundle.source_weights.items() if w > 0]
                    logger.info(f"[UNIFIED FLOW] {ticker}: sentiment={flow_sentiment}, "
                               f"score={flow_bundle.flow_score:.2f}, confidence={flow_confidence:.0f}%, "
                               f"sources={sources_active}, agreement={flow_bundle.source_agreement:.2f}")

                except Exception as e:
                    logger.warning(f"Unified flow engine error for {ticker}: {e}, falling back to legacy")
                    # Fallback to legacy flow signal
                    flow_signal = await self._get_option_flow_signal(ticker, direction)
                    flow_sentiment = flow_signal.get('flow_sentiment', 'neutral')
                    flow_confidence = flow_signal.get('flow_confidence', 50)

                    # Legacy flow boost calculation
                    flow_boost = 0
                    if direction == 'long' and flow_sentiment == 'bullish':
                        flow_boost = (flow_confidence - 50) / 100 * 0.15
                    elif direction == 'short' and flow_sentiment == 'bearish':
                        flow_boost = (flow_confidence - 50) / 100 * 0.15
                    elif direction == 'long' and flow_sentiment == 'bearish':
                        flow_boost = -0.10
                    elif direction == 'short' and flow_sentiment == 'bullish':
                        flow_boost = -0.10
            else:
                # Legacy path - no unified flow engine
                flow_signal = await self._get_option_flow_signal(ticker, direction)
                flow_boost = 0
                flow_sentiment = flow_signal.get('flow_sentiment', 'neutral')
                flow_confidence = flow_signal.get('flow_confidence', 50)

                if direction == 'long' and flow_sentiment == 'bullish':
                    flow_boost = (flow_confidence - 50) / 100 * 0.15  # Up to +15%
                elif direction == 'short' and flow_sentiment == 'bearish':
                    flow_boost = (flow_confidence - 50) / 100 * 0.15
                elif direction == 'long' and flow_sentiment == 'bearish':
                    flow_boost = -0.10  # Reduce confidence if flow is against direction
                elif direction == 'short' and flow_sentiment == 'bullish':
                    flow_boost = -0.10

            final_prob = min(0.95, max(0.40, base_prob + flow_boost))
            final_strength = base_strength + (flow_boost * 100)

            logger.info(f"[ENSEMBLE] {ticker} {direction}: base={base_prob:.2f}, "
                       f"flow={flow_sentiment}({flow_confidence:.0f}%), "
                       f"boost={flow_boost:+.2f}, final={final_prob:.2f}")

            return (final_prob, final_strength)

        if self.ensemble_scorer and self.market_data_service:
            try:
                from app.services.ensemble_scorer import SignalInput, SignalSource

                # Get market data
                etf_map = {'MES': 'SPY', 'MNQ': 'QQQ', 'MYM': 'DIA', 'MGC': 'GLD',
                          'US30': 'DIA', 'NAS100': 'QQQ', 'SPX500': 'SPY', 'US500': 'SPY',
                          'XAUUSD': 'GLD'}
                analysis_ticker = etf_map.get(ticker, ticker)

                market_data = self.market_data_service.get_market_data(analysis_ticker)

                if market_data:
                    # Create a signal input from market data
                    action = 'buy' if direction == 'long' else 'sell'

                    # Calculate base confidence from technicals
                    confidence = 50.0
                    ema_9 = market_data.get('ema_9', 0)
                    ema_20 = market_data.get('ema_20', 0)
                    rsi = market_data.get('rsi_14', 50)
                    price = market_data.get('current_price', 0)

                    # EMA alignment bonus
                    if direction == 'long' and ema_9 > ema_20 and price > ema_9:
                        confidence += 15
                    elif direction == 'short' and ema_9 < ema_20 and price < ema_9:
                        confidence += 15

                    # RSI bonus
                    if direction == 'long' and rsi < 40:
                        confidence += 10  # Oversold bounce
                    elif direction == 'short' and rsi > 60:
                        confidence += 10  # Overbought reversal

                    # Volume spike bonus
                    if market_data.get('volume_spike'):
                        confidence += 10

                    signal_strength = min(100, confidence * 1.2)

                    return (confidence / 100.0, signal_strength)

            except Exception as e:
                logger.debug(f"Ensemble scoring failed for {ticker}: {e}")

        # Default moderate values
        return (0.60, 55.0)


class LiveForwardTestRunner:
    """
    Runs the forward test strategy with live data.
    Supports dynamic strategy adjustment based on market conditions.
    NOW WITH WEBHOOK SIGNAL GENERATION for live broker execution!
    """

    def __init__(
        self,
        tickers: List[str],
        update_interval: int = 30,
        max_runtime_hours: float = 0,  # 0 = unlimited (24/7)
        dynamic_strategy: bool = True,
        log_file: str = "forward_test_state.json",
        webhook_enabled: bool = False,
        webhook_key: str = None,
        api_base_url: str = None,
        no_projectx: bool = False
    ):
        self.tickers = tickers
        self.update_interval = update_interval
        self.max_runtime = timedelta(hours=max_runtime_hours) if max_runtime_hours > 0 else None
        self.dynamic_strategy = dynamic_strategy
        self.log_file = log_file
        self.no_projectx = no_projectx

        self.data_feed = LiveDataFeed()
        self.tester = ForwardTester(ForwardTestConfig(trade_ranging=True))
        self.strategy_manager = DynamicStrategyManager() if dynamic_strategy else None

        # ===========================================================================
        # PHASE 4: Full SmartFlow Architecture Components
        # ===========================================================================
        self._use_full_architecture = USE_FULL_ARCHITECTURE and ROUTER_AVAILABLE

        # Initialize Adaptive Router
        if self._use_full_architecture:
            try:
                self._router = get_router()
                self._router.routing_mode = RoutingMode.AUTO_BY_REGIME
                logger.info("[FULL ARCH] SmartFlow Engine Router initialized (AUTO_BY_REGIME)")
            except Exception as e:
                logger.warning(f"[FULL ARCH] Router init failed, using legacy: {e}")
                self._router = None
                self._use_full_architecture = False
        else:
            self._router = None
            logger.info("[LEGACY] Using simplified signal path (router disabled)")

        # Initialize Strategy Engines (lazy - instantiated per-ticker)
        self._engine_instances: Dict[str, Any] = {}

        # Initialize Signal Intelligence Guard
        # Note: Guard is available but DB session is created per-evaluation for safety
        self._signal_guard_available = SIGNAL_GUARD_AVAILABLE and self._use_full_architecture
        if self._signal_guard_available:
            logger.info("[FULL ARCH] Signal Intelligence Guard enabled (session-per-call mode)")
        else:
            if not SIGNAL_GUARD_AVAILABLE:
                logger.warning("[FULL ARCH] Signal Guard not available: imports failed")
            elif not self._use_full_architecture:
                logger.info("[FULL ARCH] Signal Guard disabled: legacy mode")

        # Track last router decisions for logging
        self._last_router_decision: Dict[str, RouterDecision] = {}

        # Initialize Signal Agreement Layer (Quick Anchor + Regime Adaptive)
        self._signal_agreement = None
        if SIGNAL_AGREEMENT_AVAILABLE and self._use_full_architecture:
            try:
                self._signal_agreement = get_signal_agreement_layer()
                logger.info(f"[FULL ARCH] Signal Agreement Layer enabled: mode={self._signal_agreement.mode.value}")
            except Exception as e:
                logger.warning(f"[FULL ARCH] Signal Agreement init failed: {e}")

        # Track last agreement results for logging
        self._last_agreement_result: Dict[str, AgreementResult] = {}

        # Initialize AI Feature Engine (metadata-first)
        self._ai_feature_engine = None
        if AI_ENGINE_AVAILABLE and self._use_full_architecture:
            try:
                self._ai_feature_engine = get_ai_feature_engine()
                logger.info("[FULL ARCH] AI Feature Engine enabled (metadata-first)")
            except Exception as e:
                logger.warning(f"[FULL ARCH] AI Feature Engine init failed: {e}")

        # Initialize Advanced Risk Manager (metadata-first)
        self._risk_manager = None
        if RISK_ENGINE_AVAILABLE and self._use_full_architecture:
            try:
                self._risk_manager = get_advanced_risk_manager()
                logger.info("[FULL ARCH] Advanced Risk Manager enabled (metadata-first)")
            except Exception as e:
                logger.warning(f"[FULL ARCH] Advanced Risk Manager init failed: {e}")

        # Initialize Strategy Allocator reference (requires DB session per-call)
        self._allocator_available = ALLOCATOR_AVAILABLE and self._use_full_architecture
        if self._allocator_available:
            logger.info("[FULL ARCH] Strategy Allocator enabled (session-per-call mode)")

        # Initialize Portfolio Risk Engine (metadata-first + optional blocking)
        self._portfolio_risk_engine = None
        self._portfolio_risk_available = PORTFOLIO_RISK_AVAILABLE and self._use_full_architecture
        if self._portfolio_risk_available:
            try:
                self._portfolio_risk_engine = get_portfolio_risk_engine()
                logger.info("[FULL ARCH] Portfolio Risk Engine enabled (metadata-first)")
            except Exception as e:
                logger.warning(f"[FULL ARCH] Portfolio Risk Engine init failed: {e}")
                self._portfolio_risk_available = False

        # Initialize Execution Quality Tracker (metadata-first)
        self._execution_tracker = None
        self._execution_quality_available = EXECUTION_QUALITY_AVAILABLE and self._use_full_architecture
        if self._execution_quality_available:
            try:
                self._execution_tracker = get_execution_tracker()
                logger.info("[FULL ARCH] Execution Quality Tracker enabled (metadata-first)")
            except Exception as e:
                logger.warning(f"[FULL ARCH] Execution Quality Tracker init failed: {e}")
                self._execution_quality_available = False
        # ===========================================================================

        # Broker position sync (checks actual broker positions)
        self.position_sync = BrokerPositionSync()
        self._position_sync_enabled = False

        # Webhook signal sender for live broker trades
        self.webhook_enabled = webhook_enabled
        self.webhook_url = os.getenv('SMARTFLOW_WEBHOOK_URL', '')
        if webhook_enabled or self.webhook_url:
            self.webhook_sender = WebhookSignalSender(
                webhook_key=webhook_key,
                base_url=api_base_url,
                webhook_url=self.webhook_url
            )
            self.webhook_enabled = self.webhook_sender.enabled
        else:
            self.webhook_sender = None

        # Max positions per ticker (for pyramid)
        self.max_positions_per_ticker = 3

        self._running = False
        self._start_time = None
        self._last_update: Dict[str, datetime] = {}
        self._price_history: Dict[str, List[Dict]] = {t: [] for t in tickers}
        self._trade_regimes: Dict[str, str] = {}  # Track regime per trade
        self._cycles_since_save = 0

    async def start(self):
        """Start the live forward test."""
        print_banner(dynamic=self.dynamic_strategy)

        # Initialize data feeds
        if not await self.data_feed.initialize():
            logger.error("Failed to initialize data feeds")
            print("\n[ERROR] No data feeds available. Check your API credentials:")
            print("  - PROJECTX_USERNAME, PROJECTX_PASSWORD, PROJECTX_API_KEY")
            print("  - POLYGON_API_KEY")
            return

        # Initialize broker position sync
        self._position_sync_enabled = await self.position_sync.initialize()
        if self._position_sync_enabled:
            print("[POSITION SYNC] Connected to broker for position verification")
        else:
            print("[POSITION SYNC] Not available (using internal state only)")

        # Initialize direct ProjectX bracket orders for futures (with SL/TP)
        # Skip if --no-projectx flag is set (webhook only mode)
        if self.webhook_sender and not self.no_projectx:
            projectx_enabled = await self.webhook_sender.initialize_projectx_direct()
            if projectx_enabled:
                print("[PROJECTX DIRECT] Futures will use bracket orders with SL/TP")
            else:
                print("[PROJECTX DIRECT] Not available (SL/TP via webhook only)")
        elif self.no_projectx:
            print("[PROJECTX DIRECT] Disabled by --no-projectx flag (webhook only mode)")

        # Load previous state if exists
        self._load_state()

        # Start session
        self.tester.start_session(self.tickers)
        self._running = True
        self._start_time = datetime.now()

        mode = "DYNAMIC" if self.dynamic_strategy else "FIXED 2%/2%"
        runtime_str = str(self.max_runtime) if self.max_runtime else "UNLIMITED (24/7)"

        print(f"\n[STARTED] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {mode}")
        print(f"Tickers: {', '.join(self.tickers)}")
        print(f"Update Interval: {self.update_interval}s")
        print(f"Max Runtime: {runtime_str}")
        print("\nPress Ctrl+C to stop\n")

        # Setup signal handler
        def handle_signal(sig, frame):
            logger.info("Received shutdown signal")
            self._running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Main loop
        cycle = 0
        while self._running:
            cycle += 1
            await self._process_cycle(cycle)

            # Check runtime limit
            if self.max_runtime and datetime.now() - self._start_time > self.max_runtime:
                logger.info(f"Max runtime reached ({self.max_runtime})")
                break

            # Save state periodically (every 20 cycles)
            self._cycles_since_save += 1
            if self._cycles_since_save >= 20:
                self._save_state()
                self._cycles_since_save = 0

            # Wait for next update
            await asyncio.sleep(self.update_interval)

        # Final status and save
        self._save_state()
        self._print_final_status()

    def _load_state(self):
        """Load previous session state if available."""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded previous state: {state.get('total_trades', 0)} trades")
        except Exception as e:
            logger.debug(f"No previous state to load: {e}")

    def _save_state(self):
        """Save current session state."""
        try:
            status = self.tester.get_status()
            state = {
                'timestamp': datetime.now().isoformat(),
                'tickers': self.tickers,
                'dynamic_strategy': self.dynamic_strategy,
                **status
            }
            if self.strategy_manager:
                state['regime_stats'] = self.strategy_manager.get_regime_stats()
                state['current_regimes'] = {
                    t: self.strategy_manager.get_current_regime(t) for t in self.tickers
                }
            with open(self.log_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    async def _process_cycle(self, cycle: int):
        """Process one update cycle."""
        logger.debug(f"Cycle {cycle}")

        # Sync broker positions periodically
        if self._position_sync_enabled:
            sync_result = await self.position_sync.sync_positions()
            if sync_result.get('synced'):
                # Handle closed positions (detected by broker sync)
                for closed in sync_result.get('closed_positions', []):
                    ticker = closed.get('ticker')
                    logger.info(f"[BROKER SYNC] Position closed on broker: {ticker}")
                    # Clear internal state for this ticker to allow new signals
                    self._handle_broker_closed_position(ticker)

        for ticker in self.tickers:
            try:
                await self._process_ticker(ticker)
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")

        # Print status every 10 cycles
        if cycle % 10 == 0:
            self._print_status()

    def _handle_broker_closed_position(self, ticker: str):
        """Handle a position that was closed on the broker side."""
        # Find and close matching internal trades
        trades_to_close = [
            trade_id for trade_id, trade in self.tester.session.open_trades.items()
            if trade.ticker.upper() == ticker.upper()
        ]
        for trade_id in trades_to_close:
            trade = self.tester.session.open_trades.get(trade_id)
            if trade:
                # Mark as closed by broker
                trade.exit_reason = "broker_closed"
                trade.exit_time = datetime.now(EST_TZ)
                # Move to closed trades
                del self.tester.session.open_trades[trade_id]
                logger.info(f"[BROKER SYNC] Cleared internal trade {trade_id} for {ticker}")

    # ===========================================================================
    # PHASE 4: Full Architecture Signal Generation
    # ===========================================================================

    async def _generate_signal_full_arch(
        self,
        ticker: str,
        bar: Dict,
        regime: str,
        direction: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate signal using full SmartFlow architecture with Signal Agreement Layer:
        1. Generate QUICK signal (anchor) - always first
        2. Get regime_adaptive decision from router
        3. Generate regime engine signal (if different from quick)
        4. Apply Signal Agreement Layer
        5. Flow feature integration
        6. Signal guard evaluation
        7. Canonical metadata attachment

        Returns signal dict with full metadata, or None if no signal.
        """
        price = bar['close']

        # ==== STEP 1: Generate QUICK (Anchor) Signal - ALWAYS FIRST ====
        # Quick uses ensemble scoring as its signal source
        quick_direction = None
        quick_confidence = 0.0
        try:
            ensemble_prob, signal_strength = await self.data_feed.get_ensemble_score(ticker, direction)
            min_prob = 0.55
            min_strength = 50.0

            if ensemble_prob >= min_prob and signal_strength >= min_strength:
                quick_direction = direction
                quick_confidence = ensemble_prob
                logger.debug(
                    f"[QUICK ANCHOR] {ticker}: {quick_direction} "
                    f"prob={quick_confidence:.2f} strength={signal_strength:.1f}"
                )
        except Exception as e:
            logger.warning(f"[QUICK ANCHOR] Error for {ticker}: {e}")

        # ==== STEP 2: Get Router Decision (Regime Adaptive) ====
        router_decision = None
        regime_engine = None
        regime_strategy = None
        regime_direction = None
        regime_confidence = 0.0

        if self._router:
            try:
                router_decision = self._router.route_signal_request(
                    regime=regime,
                    regime_confidence=0.7
                )
                self._last_router_decision[ticker] = router_decision
                regime_engine = router_decision.selected_engine
                regime_strategy = router_decision.selected_strategy_id

                logger.debug(
                    f"[ROUTER] {ticker}: {regime} → {regime_engine} "
                    f"(strategy={regime_strategy})"
                )
            except Exception as e:
                logger.warning(f"[ROUTER] Error for {ticker}: {e}")

        # ==== STEP 3: Generate Regime Engine Signal (if specialized engine selected) ====
        if regime_engine and regime_engine not in ['quick', 'unified', 'deterministic']:
            engine_class = STRATEGY_ENGINES.get(regime_engine) if STRATEGY_ENGINES_AVAILABLE else None
            if engine_class:
                try:
                    if regime_engine not in self._engine_instances:
                        self._engine_instances[regime_engine] = engine_class()

                    engine = self._engine_instances[regime_engine]

                    if STRATEGY_ENGINES_AVAILABLE:
                        context = SignalContext(
                            ticker=ticker,
                            timestamp=datetime.now(EST_TZ),
                            close=price,
                            high=bar.get('high', price),
                            low=bar.get('low', price),
                            open=bar.get('open', price),
                            volume=bar.get('volume', 0),
                            regime=regime,
                        )

                        trading_signal = engine.generate_signal(context) if hasattr(engine, 'generate_signal') else None

                        if trading_signal and trading_signal.direction in ['long', 'short']:
                            # CRITICAL FIX: Validate engine signal matches requested direction
                            if trading_signal.direction != direction:
                                logger.debug(
                                    f"[REGIME ENGINE] {regime_engine} for {ticker}: "
                                    f"REJECTED - engine wants {trading_signal.direction} but "
                                    f"regime requires {direction}"
                                )
                            else:
                                regime_direction = trading_signal.direction
                                regime_confidence = trading_signal.confidence
                                logger.debug(
                                    f"[REGIME ENGINE] {regime_engine} for {ticker}: "
                                    f"{regime_direction} conf={regime_confidence:.2f}"
                                )
                except Exception as e:
                    logger.warning(f"[REGIME ENGINE] {regime_engine} error for {ticker}: {e}")

        # ==== STEP 4: Apply Signal Agreement Layer ====
        agreement_result = None
        final_direction = quick_direction
        final_confidence = quick_confidence
        size_multiplier = 1.0

        if self._signal_agreement and quick_direction:
            try:
                agreement_result = evaluate_signal_agreement(
                    anchor_direction=quick_direction,
                    anchor_confidence=quick_confidence,
                    regime_strategy=regime_strategy,
                    regime_engine=regime_engine,
                    regime_direction=regime_direction,
                    regime_confidence=regime_confidence,
                    current_regime=regime,
                )
                self._last_agreement_result[ticker] = agreement_result

                # Apply agreement decision
                if agreement_result.final_decision == FinalDecision.SKIP:
                    logger.info(f"[AGREEMENT] {ticker}: SKIP - {agreement_result.reason}")
                    return None
                elif agreement_result.final_decision == FinalDecision.REDUCE:
                    size_multiplier = agreement_result.size_multiplier
                    final_confidence = agreement_result.final_confidence
                elif agreement_result.final_decision in [FinalDecision.BOOST, FinalDecision.EXECUTE]:
                    size_multiplier = agreement_result.size_multiplier
                    final_confidence = agreement_result.final_confidence

            except Exception as e:
                logger.warning(f"[AGREEMENT] Error for {ticker}: {e}")
                # Continue with quick signal on agreement error

        # If no quick signal, no trade
        if not quick_direction:
            return None

        # ==== STEP 5: Build Signal Dict ====
        signal = {
            'ticker': ticker,
            'direction': final_direction,
            'price': price,
            'entry_price': price,
            'action': 'buy' if final_direction == 'long' else 'sell',
            'ensemble_prob': final_confidence,
            'regime': regime,
            'size_multiplier': size_multiplier,
        }

        # ==== STEP 6: Get Flow Features ====
        flow_bundle = None
        flow_sentiment = 'neutral'
        flow_confidence = 0.5
        if FLOW_ENGINE_AVAILABLE and self.data_feed.flow_feature_engine:
            try:
                flow_bundle = self.data_feed.flow_feature_engine.get_flow_feature_bundle(ticker)
                if flow_bundle:
                    flow_sentiment = flow_bundle.sentiment.value if hasattr(flow_bundle.sentiment, 'value') else str(flow_bundle.sentiment)
                    flow_confidence = flow_bundle.confidence
            except Exception as e:
                logger.debug(f"[FLOW] Error for {ticker}: {e}")

        # ==== STEP 6.5: AI Feature Engine (metadata-first) ====
        ai_features = {}
        if self._ai_feature_engine:
            try:
                ai_features = self._ai_feature_engine.get_feature_dict(ticker, regime)
                logger.debug(
                    f"[AI FEATURES] {ticker}: bias={ai_features.get('overall_ai_bias', 0):.3f} "
                    f"conf={ai_features.get('confidence', 0):.2f}"
                )
            except Exception as e:
                logger.debug(f"[AI FEATURES] Error for {ticker}: {e}")

        # ==== STEP 6.6: Strategy Allocator (metadata-first, session-per-call) ====
        allocation_decision = None
        allocation_weight = 1.0
        allocation_score = 0.0
        if self._allocator_available:
            db_session = None
            try:
                db_session = SessionLocal()
                allocator = StrategyAllocator(db_session)
                allocation_decision = allocator.compute_allocation(
                    strategy_ids=[regime_strategy] if regime_strategy else None,
                    engine_type=regime_engine,
                    regime=regime,
                    regime_confidence=router_decision.statistical_confidence if router_decision else 0.7,
                    ai_features=ai_features if ai_features else None
                )
                if allocation_decision and allocation_decision.selected_strategies:
                    allocation_weight = allocation_decision.selected_strategies[0].allocation_weight
                    allocation_score = allocation_decision.selected_strategies[0].adjusted_score
                    logger.debug(
                        f"[ALLOCATOR] {ticker}: weight={allocation_weight:.3f} "
                        f"score={allocation_score:.3f}"
                    )
            except Exception as e:
                logger.debug(f"[ALLOCATOR] Error for {ticker}: {e}")
            finally:
                if db_session:
                    db_session.close()

        # ==== STEP 6.7: Advanced Risk Manager (metadata-first) ====
        risk_assessment = None
        risk_final_size_pct = 2.0
        risk_adjustments = []
        if self._risk_manager:
            try:
                # Calculate stop price for risk assessment
                stop_pct = 2.0  # Default, will be updated in step 7
                if final_direction == 'long':
                    stop_price_est = price * (1 - stop_pct / 100)
                else:
                    stop_price_est = price * (1 + stop_pct / 100)

                risk_assessment = self._risk_manager.calculate_position_size(
                    ticker=ticker,
                    entry_price=price,
                    stop_loss=stop_price_est,
                    confidence=final_confidence,
                    capital=100000,  # Forward test placeholder capital
                    base_size_pct=2.0,
                    strategy=regime_strategy or 'quick'
                )
                risk_final_size_pct = risk_assessment.get('final_size_pct', 2.0)
                risk_adjustments = risk_assessment.get('adjustments', [])
                if risk_adjustments:
                    logger.debug(f"[RISK] {ticker}: {risk_adjustments}")
            except Exception as e:
                logger.debug(f"[RISK] Error for {ticker}: {e}")

        # ==== STEP 6.8: Portfolio Risk Engine (metadata-first + optional blocking) ====
        portfolio_risk_snapshot = None
        portfolio_risk_adjustment = 1.0
        portfolio_risk_blocked = False
        portfolio_risk_reason = ""
        portfolio_risk_budget_used = 0.0
        if self._portfolio_risk_available and self._portfolio_risk_engine:
            db_session = None
            try:
                db_session = SessionLocal()
                # Build strategy allocations from current signal
                strategy_allocations = {}
                if regime_strategy:
                    strategy_allocations[regime_strategy] = allocation_weight
                else:
                    strategy_allocations['quick'] = 1.0

                portfolio_risk_snapshot = self._portfolio_risk_engine.calculate_portfolio_risk(
                    db=db_session,
                    strategy_allocations=strategy_allocations
                )

                # Extract key metrics
                portfolio_risk_budget_used = portfolio_risk_snapshot.risk_budget_used
                portfolio_risk_blocked = portfolio_risk_snapshot.is_halted
                portfolio_risk_reason = portfolio_risk_snapshot.halt_reason or "within_limits"

                # Calculate adjustment based on risk budget usage
                # If budget > 80% used, start reducing; if halted, block
                if portfolio_risk_blocked:
                    portfolio_risk_adjustment = 0.0
                    logger.warning(
                        f"[PORTFOLIO RISK] {ticker}: BLOCKED - {portfolio_risk_reason}"
                    )
                elif portfolio_risk_budget_used > 80:
                    # Scale down proportionally
                    portfolio_risk_adjustment = max(0.5, 1.0 - (portfolio_risk_budget_used - 80) / 40)
                    portfolio_risk_reason = f"budget_high ({portfolio_risk_budget_used:.1f}%)"
                    logger.info(
                        f"[PORTFOLIO RISK] {ticker}: adjustment={portfolio_risk_adjustment:.2f} "
                        f"blocked={portfolio_risk_blocked} reason={portfolio_risk_reason}"
                    )
                else:
                    logger.debug(
                        f"[PORTFOLIO RISK] {ticker}: budget={portfolio_risk_budget_used:.1f}% "
                        f"vol={portfolio_risk_snapshot.portfolio_volatility:.4f}"
                    )
            except Exception as e:
                logger.debug(f"[PORTFOLIO RISK] Error for {ticker}: {e}")
            finally:
                if db_session:
                    db_session.close()

        # ==== STEP 6.9: Execution Quality Tracker (metadata-first) ====
        execution_quality = None
        execution_quality_score = 100.0
        expected_slippage_bps = 0.0
        execution_adjustment = 1.0
        execution_reason = "no_history"
        execution_blocked = False
        if self._execution_quality_available and self._execution_tracker:
            try:
                strategy_id = regime_strategy or 'quick'
                execution_quality = self._execution_tracker.calculate_strategy_quality(
                    strategy_id=strategy_id,
                    lookback_trades=50
                )

                execution_quality_score = execution_quality.execution_quality_score
                expected_slippage_bps = execution_quality.avg_slippage_bps

                # Calculate adjustment based on quality score
                # Score < 50 = poor execution quality, reduce or block
                if execution_quality_score >= 80:
                    execution_adjustment = 1.0
                    execution_reason = "good_quality"
                elif execution_quality_score >= 50:
                    execution_adjustment = 0.8 + (execution_quality_score - 50) / 150
                    execution_reason = f"moderate_quality ({execution_quality_score:.0f})"
                else:
                    # Very poor quality - flag for review but don't block
                    execution_adjustment = 0.6
                    execution_reason = f"poor_quality ({execution_quality_score:.0f})"

                # Optional blocking for very poor quality (disabled by default)
                # if execution_quality_score < 30:
                #     execution_blocked = True
                #     execution_reason = f"blocked: quality={execution_quality_score:.0f}"

                logger.info(
                    f"[EXECUTION QUALITY] {ticker}: score={execution_quality_score:.1f} "
                    f"slip={expected_slippage_bps:.1f}bps adjust={execution_adjustment:.2f}"
                )
            except Exception as e:
                logger.debug(f"[EXECUTION QUALITY] Error for {ticker}: {e}")

        # Check for portfolio risk blocking (optional - currently metadata-first)
        # Uncomment to enable blocking:
        # if portfolio_risk_blocked:
        #     logger.warning(f"[PORTFOLIO RISK] {ticker}: BLOCKED - {portfolio_risk_reason}")
        #     return None

        # ==== STEP 7: Apply dynamic stop/target ====
        if self.strategy_manager:
            volatility = ((bar['high'] - bar['low']) / price) * 100 if price > 0 else 1.0
            params = self.strategy_manager.get_strategy_params(ticker, regime, volatility)
            signal['stop_pct'] = params['stop_pct']
            signal['target_pct'] = params['target_pct']
        else:
            signal['stop_pct'] = 2.0
            signal['target_pct'] = 2.0

        # ==== STEP 8: Attach Canonical Metadata (CRITICAL for traceability) ====
        signal['_metadata'] = {
            # Anchor (Quick) Engine - PRIMARY
            'anchor_engine': 'quick',
            'anchor_direction': quick_direction,
            'anchor_confidence': quick_confidence,

            # Router Decision (Regime Adaptive)
            'selected_strategy_id': router_decision.selected_strategy_id if router_decision else None,
            'selected_engine': router_decision.selected_engine if router_decision else None,
            'strategy_status': router_decision.strategy_status if router_decision else None,
            'current_regime': router_decision.current_regime if router_decision else regime,
            'router_mode': router_decision.routing_mode.value if router_decision else 'manual',
            'decision_source': router_decision.decision_source.value if router_decision else 'fallback',
            'router_confidence': router_decision.statistical_confidence if router_decision else 0.0,

            # Regime Engine Output
            'regime_engine': regime_engine,
            'regime_strategy': regime_strategy,
            'regime_direction': regime_direction,
            'regime_confidence': regime_confidence,

            # Signal Agreement Layer
            'agreement_state': agreement_result.agreement_state.value if agreement_result else 'not_applied',
            'agreement_score': agreement_result.agreement_score if agreement_result else 0.0,
            'agreement_decision': agreement_result.final_decision.value if agreement_result else 'execute',
            'agreement_size_multiplier': agreement_result.size_multiplier if agreement_result else 1.0,
            'agreement_confidence_adjustment': agreement_result.confidence_adjustment if agreement_result else 0.0,
            'agreement_reason': agreement_result.reason if agreement_result else 'agreement layer disabled',

            # Flow Data
            'flow_sentiment': flow_sentiment,
            'flow_confidence': flow_confidence,

            # AI Feature Engine (metadata-first)
            'ai_technical_score': ai_features.get('technical_score', 0.0),
            'ai_pattern_edge_score': ai_features.get('pattern_edge_score', 0.0),
            'ai_macro_risk_score': ai_features.get('macro_risk_score', 0.0),
            'ai_macro_bias_score': ai_features.get('macro_bias_score', 0.0),
            'ai_overall_bias': ai_features.get('overall_ai_bias', 0.0),
            'ai_confidence': ai_features.get('confidence', 0.0),

            # Strategy Allocator (metadata-first)
            'allocator_weight': allocation_weight,
            'allocator_score': allocation_score,
            'allocator_excluded_count': len(allocation_decision.excluded_strategies) if allocation_decision else 0,
            'allocator_selected_count': len(allocation_decision.selected_strategies) if allocation_decision else 0,

            # Advanced Risk Manager (metadata-first)
            'risk_final_size_pct': risk_final_size_pct,
            'risk_adjustments': risk_adjustments,
            'risk_cvar_applied': bool(risk_assessment.get('cvar_result')) if risk_assessment else False,
            'risk_slippage_est': risk_assessment.get('slippage_estimate').expected_ticks if risk_assessment and risk_assessment.get('slippage_estimate') else 0.0,

            # Portfolio Risk Engine (metadata-first + optional blocking)
            'portfolio_risk_adjustment': portfolio_risk_adjustment,
            'portfolio_risk_blocked': portfolio_risk_blocked,
            'portfolio_risk_reason': portfolio_risk_reason,
            'portfolio_risk_budget_used': portfolio_risk_budget_used,

            # Execution Quality Tracker (metadata-first)
            'execution_quality_score': execution_quality_score,
            'expected_slippage_bps': expected_slippage_bps,
            'execution_adjustment': execution_adjustment,
            'execution_reason': execution_reason,
            'execution_blocked': execution_blocked,

            # Final Computed Values
            'final_direction': final_direction,
            'final_confidence': final_confidence,
            'size_multiplier': size_multiplier,

            # Guard Status (will be updated in step 9)
            'guard_status': 'pending',
            'guard_checks': [],

            # Timestamp
            'generated_at': datetime.now(EST_TZ).isoformat(),
        }

        # ==== STEP 9: Signal Intelligence Guard (with DB session) ====
        if self._signal_guard_available:
            db_session = None
            try:
                # Create DB session for this guard call
                db_session = SessionLocal()

                # Create Signal domain entity from our signal dict
                signal_action = SignalAction.BUY if direction == 'long' else SignalAction.SELL
                signal_entity = Signal(
                    id=SignalId(str(uuid.uuid4())),
                    source=SignalSource.CUSTOM,
                    symbol=Symbol(ticker),
                    action=signal_action,
                    volume=Volume(Decimal('1')),  # Forward test uses 1 contract
                    price=Price(Decimal(str(price))),
                    strategy_id=signal.get('_metadata', {}).get('selected_strategy_id', 'forward_test'),
                    raw_payload=signal,
                )

                # Initialize guard with DB session
                guard = SignalIntelligenceGuard(db=db_session)

                # Evaluate signal - forward test uses synthetic user_id=0, no real accounts
                guard_result: GuardResult = await guard.evaluate(
                    signal=signal_entity,
                    user_id=FORWARD_TEST_USER_ID,
                    account_ids=[],  # Forward test has no real accounts
                    open_positions_summary=None
                )

                # Map GuardDecision to status
                if guard_result.decision == GuardDecision.EXECUTE:
                    signal['_metadata']['guard_status'] = 'allowed'
                    signal['_metadata']['guard_decision'] = 'execute'
                    logger.info(f"[GUARD] {ticker} {direction}: ALLOWED")
                elif guard_result.decision == GuardDecision.SKIP:
                    signal['_metadata']['guard_status'] = 'blocked'
                    signal['_metadata']['guard_decision'] = 'skip'
                    signal['_metadata']['guard_reason'] = guard_result.annotations.get('discard_reason', 'skipped')
                    logger.info(f"[GUARD] {ticker} {direction}: BLOCKED reason={guard_result.annotations.get('history_tag', 'unknown')}")
                    return None  # Block signal
                elif guard_result.decision == GuardDecision.PAUSE_NEW_ENTRIES:
                    signal['_metadata']['guard_status'] = 'paused'
                    signal['_metadata']['guard_decision'] = 'pause_new_entries'
                    signal['_metadata']['guard_reason'] = guard_result.annotations.get('history_tag', 'paused')
                    logger.info(f"[GUARD] {ticker} {direction}: PAUSED reason={guard_result.annotations.get('history_tag', 'unknown')}")
                    return None  # Block signal during pause
                elif guard_result.decision == GuardDecision.WARN_MODAL_REQUIRED:
                    # In forward test, auto-proceed with warnings (no UI to show modal)
                    signal['_metadata']['guard_status'] = 'warned'
                    signal['_metadata']['guard_decision'] = 'warn_modal_required'
                    signal['_metadata']['guard_warning'] = guard_result.modal_data
                    logger.info(f"[GUARD] {ticker} {direction}: WARNED (auto-proceeding) modal={guard_result.modal_data.get('type', 'unknown') if guard_result.modal_data else 'none'}")
                else:
                    signal['_metadata']['guard_status'] = 'unknown'
                    signal['_metadata']['guard_decision'] = str(guard_result.decision)

                # Capture any annotations
                signal['_metadata']['guard_annotations'] = guard_result.annotations

            except Exception as e:
                error_str = str(e)
                # Check for missing tables (migration not run)
                if 'UndefinedTable' in error_str or 'does not exist' in error_str:
                    # Signal Intelligence tables not migrated - fail safely
                    logger.warning(f"[GUARD] Tables not available (migration 018 required): {ticker}")
                    signal['_metadata']['guard_status'] = 'tables_missing'
                    signal['_metadata']['guard_note'] = 'Run alembic migration 018 to enable Signal Guard'
                else:
                    logger.warning(f"[GUARD] Error evaluating {ticker}: {e}")
                    signal['_metadata']['guard_status'] = 'error'
                    signal['_metadata']['guard_error'] = error_str
            finally:
                # Always close DB session
                if db_session:
                    db_session.close()
        else:
            signal['_metadata']['guard_status'] = 'not_available'

        return signal

    # ===========================================================================

    async def _process_ticker(self, ticker: str):
        """Process one ticker update with dynamic strategy adjustment."""
        # Get current bar
        bar = await self.data_feed.get_ohlc(ticker)
        if not bar:
            logger.warning(f"No data for {ticker}")
            return

        price = bar['close']
        high = bar['high']
        low = bar['low']

        # Get regime and calculate volatility
        regime = await self.data_feed.get_regime(ticker)

        # Calculate volatility from price range
        volatility = ((high - low) / price) * 100 if price > 0 else 1.0

        # Get dynamic strategy parameters
        if self.strategy_manager:
            params = self.strategy_manager.get_strategy_params(ticker, regime, volatility)
            strategy_label = f"{params['strategy']}({params['stop_pct']:.1f}%/{params['target_pct']:.1f}%)"
        else:
            params = {'stop_pct': 2.0, 'target_pct': 2.0, 'strategy': 'FIXED'}
            strategy_label = "FIXED(2%/2%)"

        # Check for exits first
        closed_trades = self.tester.check_exits(ticker, high, low, price)
        for trade in closed_trades:
            result = "WIN" if trade.pnl > 0 else "LOSS"
            trade_regime = self._trade_regimes.get(str(trade.id), regime)
            print(f"  [EXIT] {ticker} {result} P&L=${trade.pnl:.2f} ({trade.exit_reason}) [{trade_regime}]")

            # Send close signal to webhook for live trades
            if self.webhook_sender and self.webhook_sender.enabled:
                await self.webhook_sender.send_signal(
                    ticker=ticker,
                    action='close',
                    price=trade.exit_price or price,
                    comment=f"SmartFlow exit: {trade.exit_reason} P&L=${trade.pnl:.2f}"
                )

            # Record regime performance
            if self.strategy_manager:
                self.strategy_manager.record_trade_result(
                    ticker, trade_regime, trade.pnl, trade.pnl > 0
                )

        # Check for pyramid add-ons
        ensemble_prob, signal_strength = await self.data_feed.get_ensemble_score(ticker, 'long')

        addon = self.tester.check_pyramid_addon(
            ticker=ticker,
            high=high,
            low=low,
            close=price,
            regime=regime,
            ensemble_prob=ensemble_prob
        )
        if addon:
            trade = self.tester.execute_entry(addon)
            self._trade_regimes[str(trade.id)] = regime
            print(f"  [ADD-ON] {ticker} {addon['direction'].upper()} @ {price:.2f} "
                  f"[{strategy_label}]")

            # Send add-on signal to webhook for live trades
            if self.webhook_sender and self.webhook_sender.enabled:
                action = 'buy' if addon['direction'] == 'long' else 'sell'
                await self.webhook_sender.send_signal(
                    ticker=ticker,
                    action=action,
                    price=price,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    comment=f"SmartFlow add-on [{strategy_label}]"
                )

        # Check for new entries (only if we have available slots)
        existing = [t for t in self.tester.session.open_trades.values() if t.ticker == ticker]
        internal_count = len(existing)

        # Also check broker positions (if sync enabled) to get accurate count
        if self._position_sync_enabled:
            broker_count = self.position_sync.get_broker_position_count(ticker)
            available_slots = self.max_positions_per_ticker - max(internal_count, broker_count)
        else:
            available_slots = self.max_positions_per_ticker - internal_count

        # Log position status for debugging
        broker_count_val = broker_count if self._position_sync_enabled else 0
        if internal_count > 0 or broker_count_val > 0:
            logger.debug(f"[{ticker}] Positions - Internal: {internal_count}, "
                        f"Broker: {broker_count_val if self._position_sync_enabled else 'N/A'}, "
                        f"Available: {available_slots}")

        if available_slots > 0:
            # =======================================================================
            # PHASE 4: Full Architecture vs Legacy Path
            # =======================================================================
            if self._use_full_architecture:
                # FULL ARCHITECTURE PATH
                # Uses: Router → Engine → Guard → Canonical Metadata
                # CRITICAL FIX: Respect regime direction - only trade WITH the trend
                if regime in ['trending_up', 'breakout']:
                    directions_to_check = ['long']  # Only long in uptrends
                elif regime == 'trending_down':
                    directions_to_check = ['short']  # Only short in downtrends
                elif regime == 'ranging':
                    directions_to_check = ['long', 'short']  # Mean reversion both ways
                else:
                    directions_to_check = ['long']  # Default to long for unknown regimes

                # RANGING FIX: For mean reversion, compare BOTH directions and pick better one
                if regime == 'ranging':
                    long_signal = await self._generate_signal_full_arch(
                        ticker=ticker, bar=bar, regime=regime, direction='long'
                    )
                    short_signal = await self._generate_signal_full_arch(
                        ticker=ticker, bar=bar, regime=regime, direction='short'
                    )

                    # Pick the signal with higher confidence/probability
                    if long_signal and short_signal:
                        long_conf = long_signal.get('ensemble_prob', 0)
                        short_conf = short_signal.get('ensemble_prob', 0)
                        signal = long_signal if long_conf >= short_conf else short_signal
                        logger.info(
                            f"[RANGING] {ticker}: long={long_conf:.2f} vs short={short_conf:.2f} "
                            f"→ chose {signal['direction'].upper()}"
                        )
                    elif long_signal:
                        signal = long_signal
                    elif short_signal:
                        signal = short_signal
                    else:
                        signal = None
                else:
                    # TRENDING: Only check the single allowed direction
                    signal = None
                    for direction in directions_to_check:
                        signal = await self._generate_signal_full_arch(
                            ticker=ticker,
                            bar=bar,
                            regime=regime,
                            direction=direction
                        )
                        if signal:
                            break

                if signal:
                    # Get canonical metadata
                    metadata = signal.get('_metadata', {})
                    selected_engine = metadata.get('selected_engine', 'unified')
                    engine_confidence = metadata.get('engine_confidence', 0.5)

                    # ============================================================
                    # AGENTIC MONITOR: Validate signal BEFORE execution
                    # ============================================================
                    monitor_approved = True
                    if MONITOR_AVAILABLE:
                        should_execute, validation_msg = validate_before_trade(
                            ticker=ticker,
                            direction=signal['direction'],
                            regime=regime,
                            confidence=engine_confidence,
                            engine=selected_engine,
                            price=price,
                            metadata=metadata
                        )
                        if not should_execute:
                            logger.warning(
                                f"🛑 [MONITOR BLOCKED] {ticker} {signal['direction']}: {validation_msg}"
                            )
                            monitor_approved = False

                    if monitor_approved:
                        # Execute trade (passed monitor validation)
                        trade = self.tester.execute_entry(signal)

                        # Record in agentic monitor
                        if MONITOR_AVAILABLE:
                            monitor = get_agentic_monitor()
                            monitor.record_trade_entry(
                                ticker=ticker,
                                direction=signal['direction'],
                                entry_price=price,
                                regime=regime,
                                engine=selected_engine,
                                trade_id=str(trade.id)
                            )
                        self._trade_regimes[str(trade.id)] = regime

                        # Enhanced logging with router info
                        print(
                            f"  [ENTRY] {ticker} {signal['direction'].upper()} @ {price:.2f} "
                            f"[{selected_engine}] (conf={engine_confidence:.0%}) "
                            f"regime={regime}"
                        )
                        logger.info(
                            f"[FULL ARCH] Signal executed: {ticker} {signal['direction']} "
                            f"engine={selected_engine} strategy={metadata.get('selected_strategy_id', 'N/A')} "
                            f"guard={metadata.get('guard_status', 'N/A')}"
                        )

                        # Send entry signal to webhook with canonical metadata
                        if self.webhook_sender and self.webhook_sender.enabled:
                            action = 'buy' if signal['direction'] == 'long' else 'sell'

                            # Build comment with canonical info
                            comment = (
                                f"SmartFlow [{selected_engine}] "
                                f"strategy={metadata.get('selected_strategy_id', 'unified_v1')} "
                                f"regime={regime} "
                                f"conf={engine_confidence:.0%} "
                                f"guard={metadata.get('guard_status', 'ok')}"
                            )

                            await self.webhook_sender.send_signal(
                                ticker=ticker,
                                action=action,
                                price=price,
                                stop_loss=trade.stop_loss,
                                take_profit=trade.take_profit,
                                comment=comment,
                                strategy_id=metadata.get('selected_strategy_id', 'smartflow_forward_test')
                            )
            else:
                # LEGACY PATH (fallback)
                # Uses: Local ensemble scoring → Threshold check
                # CRITICAL FIX: Respect regime direction
                if regime == 'ranging':
                    long_prob, long_str = await self.data_feed.get_ensemble_score(ticker, 'long')
                    short_prob, short_str = await self.data_feed.get_ensemble_score(ticker, 'short')
                    if long_prob > short_prob:
                        directions = [('long', long_prob, long_str)]
                    else:
                        directions = [('short', short_prob, short_str)]
                elif regime in ['trending_up', 'breakout']:
                    # Only long in uptrends
                    prob, strength = await self.data_feed.get_ensemble_score(ticker, 'long')
                    directions = [('long', prob, strength)]
                elif regime == 'trending_down':
                    # Only short in downtrends
                    prob, strength = await self.data_feed.get_ensemble_score(ticker, 'short')
                    directions = [('short', prob, strength)]
                else:
                    # Unknown regime - default to long
                    prob, strength = await self.data_feed.get_ensemble_score(ticker, 'long')
                    directions = [('long', prob, strength)]

                for direction, ensemble_prob, signal_strength in directions:
                    signal = self.tester.check_entry_signal(
                        ticker=ticker,
                        price=price,
                        regime=regime,
                        ensemble_prob=ensemble_prob,
                        signal_strength=signal_strength
                    )
                    if signal:
                        if regime == 'ranging':
                            signal['direction'] = direction

                        if self.strategy_manager and params:
                            signal['stop_pct'] = params['stop_pct']
                            signal['target_pct'] = params['target_pct']
                            signal['strategy'] = params.get('strategy', 'TRENDING')
                            signal['size_mult'] = params.get('size_mult', 1.0)

                        signal['volatility'] = volatility
                        signal['atr_pct'] = volatility
                        signal['price_change_24h'] = bar.get('price_change_24h')
                        signal['volume_ratio'] = bar.get('volume_ratio')

                        trade = self.tester.execute_entry(signal)
                        self._trade_regimes[str(trade.id)] = regime

                        print(f"  [ENTRY] {ticker} {signal['direction'].upper()} @ {price:.2f} "
                              f"[{strategy_label}] (prob={ensemble_prob:.0%}) [LEGACY]")

                        if self.webhook_sender and self.webhook_sender.enabled:
                            action = 'buy' if signal['direction'] == 'long' else 'sell'
                            await self.webhook_sender.send_signal(
                                ticker=ticker,
                                action=action,
                                price=price,
                                stop_loss=trade.stop_loss,
                                take_profit=trade.take_profit,
                                comment=f"SmartFlow entry [{strategy_label}] prob={ensemble_prob:.0%}"
                            )

                        break
            # =======================================================================

        self._last_update[ticker] = datetime.now()

    def _get_data_delay_stats(self) -> Dict[str, Any]:
        """Get data delay statistics from flow services."""
        delay_stats = {}

        try:
            from app.services.polygon_options_flow import get_polygon_flow_service
            polygon_service = get_polygon_flow_service()
            delay_stats['polygon'] = polygon_service.get_delay_stats()
        except Exception as e:
            logger.debug(f"Could not get Polygon delay stats: {e}")

        try:
            from app.services.unusual_whales_service import get_unusual_whales_service_sync
            uw_service = get_unusual_whales_service_sync()
            delay_stats['unusual_whales'] = uw_service.get_delay_stats()
        except Exception as e:
            logger.debug(f"Could not get Unusual Whales delay stats: {e}")

        return delay_stats

    def _format_delay_status(self, delay_stats: Dict[str, Any]) -> str:
        """Format delay stats for display."""
        parts = []
        for source, stats in delay_stats.items():
            if stats.get('samples', 0) > 0:
                avg = stats.get('avg_delay_seconds', 0)
                if avg < 30:
                    status_icon = "✓"
                elif avg < 120:
                    status_icon = "⚡"
                elif avg < 900:
                    status_icon = "⚠️"
                else:
                    status_icon = "🔴"
                parts.append(f"{source[:3].upper()}:{avg:.0f}s{status_icon}")
        return " | ".join(parts) if parts else "No data delay samples yet"

    def _print_status(self):
        """Print current status with regime info."""
        status = self.tester.get_status()
        runtime = datetime.now() - self._start_time

        print(f"\n--- Status @ {datetime.now().strftime('%H:%M:%S')} (runtime: {runtime}) ---")
        print(f"Capital: ${status['capital']:,.2f} | P&L: ${status['total_pnl']:+,.2f}")
        print(f"Trades: {status['total_trades']} | Win Rate: {status['win_rate']:.1f}%")
        print(f"Open: {status['open_positions']} | Daily P&L: ${status['daily_pnl']:+,.2f}")
        print(f"Max DD: {status['max_drawdown']:.1f}%")

        # Show data delay stats
        delay_stats = self._get_data_delay_stats()
        if delay_stats:
            print(f"Data Delays: {self._format_delay_status(delay_stats)}")

        # Show broker position sync status
        if self._position_sync_enabled:
            sync_info = []
            for ticker in self.tickers:
                broker_count = self.position_sync.get_broker_position_count(ticker)
                if broker_count > 0:
                    sync_info.append(f"{ticker}:{broker_count}")
            if sync_info:
                print(f"Broker Positions: {' | '.join(sync_info)}")
            else:
                print(f"Broker Positions: None open")

        # Show current regimes if dynamic
        if self.strategy_manager:
            regimes = []
            for ticker in self.tickers:
                regime = self.strategy_manager.get_current_regime(ticker)
                regimes.append(f"{ticker}:{regime[:4]}")
            print(f"Regimes: {' | '.join(regimes)}")

            # Show regime performance every 30 cycles
            if hasattr(self, '_status_count'):
                self._status_count += 1
            else:
                self._status_count = 1

            if self._status_count % 3 == 0:
                for ticker in self.tickers:
                    stats = self.strategy_manager.get_regime_stats(ticker)
                    if stats:
                        parts = []
                        for regime, data in stats.items():
                            wr = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
                            parts.append(f"{regime[:4]}:{data['trades']}t/{wr:.0f}%")
                        if parts:
                            print(f"  {ticker}: {' '.join(parts)}")

    def _print_final_status(self):
        """Print final status report."""
        status = self.tester.get_status()
        runtime = datetime.now() - self._start_time

        print("\n" + "=" * 70)
        print("FORWARD TEST COMPLETE")
        print("=" * 70)
        print(f"\nSession: {status['session_id']}")
        print(f"Runtime: {runtime}")
        print(f"Mode: {'DYNAMIC' if self.dynamic_strategy else 'FIXED 2%/2%'}")
        print(f"\nFinal Capital: ${status['capital']:,.2f}")
        print(f"Total P&L: ${status['total_pnl']:+,.2f}")
        print(f"Total Trades: {status['total_trades']}")
        print(f"Win Rate: {status['win_rate']:.1f}%")
        print(f"Max Drawdown: {status['max_drawdown']:.1f}%")

        # Data delay verification summary
        delay_stats = self._get_data_delay_stats()
        if delay_stats:
            print("\nData Delay Verification:")
            for source, stats in delay_stats.items():
                if stats.get('samples', 0) > 0:
                    avg = stats.get('avg_delay_seconds', 0)
                    min_d = stats.get('min_delay_seconds', 0)
                    max_d = stats.get('max_delay_seconds', 0)

                    if avg < 30:
                        status = "✓ REAL-TIME"
                    elif avg < 120:
                        status = "⚡ NEAR REAL-TIME"
                    elif avg < 900:
                        status = "⚠️ DELAYED (1-15 min)"
                    else:
                        status = "🔴 15-MINUTE DELAYED"

                    print(f"  {source.upper()}: Avg={avg:.1f}s Min={min_d:.1f}s Max={max_d:.1f}s "
                          f"({stats.get('samples', 0)} samples) - {status}")
                else:
                    print(f"  {source.upper()}: No data samples collected")

        # Regime performance breakdown
        if self.strategy_manager:
            print("\nPerformance by Regime:")
            for ticker in self.tickers:
                stats = self.strategy_manager.get_regime_stats(ticker)
                if stats:
                    print(f"\n  {ticker}:")
                    for regime, data in stats.items():
                        wr = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
                        print(f"    {regime}: {data['trades']} trades, "
                              f"{wr:.1f}% WR, ${data['total_pnl']:+,.2f}")

        # Open positions
        if status['open_positions'] > 0:
            print(f"\nOpen Positions: {status['open_positions']}")
            for trade_id, trade in self.tester.session.open_trades.items():
                trade_regime = self._trade_regimes.get(str(trade_id), 'unknown')
                print(f"  - {trade.ticker} {trade.direction} @ {trade.entry_price:.2f} [{trade_regime}]")

        print(f"\nState file: {self.log_file}")
        print("=" * 70)


async def main():
    parser = argparse.ArgumentParser(description='SmartFlow Dynamic Forward Test Runner')
    parser.add_argument(
        '--tickers',
        nargs='+',
        default=['US30', 'NAS100', 'SPX500', 'US500', 'XAUUSD', 'USDJPY', 'GBPJPY', 'BTCUSD', 'ETHUSD'],
        help='Tickers to trade (default: indices + forex + crypto for 24/7 coverage)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Update interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--hours',
        type=float,
        default=0,
        help='Max runtime in hours (0 = unlimited, default: 0)'
    )
    parser.add_argument(
        '--dynamic',
        action='store_true',
        default=True,
        help='Enable dynamic strategy adjustment (default: True)'
    )
    parser.add_argument(
        '--fixed',
        action='store_true',
        help='Use fixed 2%%/2%% strategy (disables dynamic)'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as background daemon (detaches from terminal)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current session status and exit'
    )
    parser.add_argument(
        '--webhook',
        action='store_true',
        help='Enable webhook signal generation for live broker trades'
    )
    parser.add_argument(
        '--webhook-key',
        type=str,
        default=None,
        help='Webhook key for authentication (or set SMARTFLOW_WEBHOOK_KEY env var)'
    )
    parser.add_argument(
        '--api-url',
        type=str,
        default=None,
        help='API base URL for webhook (or set API_BASE_URL env var, default: http://localhost:8000)'
    )
    parser.add_argument(
        '--no-projectx',
        action='store_true',
        help='Disable direct ProjectX order placement (webhook only mode)'
    )

    args = parser.parse_args()

    # Show status
    if args.status:
        tester = ForwardTester()
        status = tester.get_status()
        log_file = "forward_test_state.json"

        # Also try to read saved state
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    state = json.load(f)
                    print("\n" + "=" * 60)
                    print("SMARTFLOW FORWARD TEST STATUS")
                    print("=" * 60)
                    print(f"Last Update: {state.get('timestamp', 'N/A')}")
                    print(f"Tickers: {', '.join(state.get('tickers', []))}")
                    print(f"Mode: {'DYNAMIC' if state.get('dynamic_strategy') else 'FIXED'}")
                    print(f"\nCapital: ${state.get('capital', 0):,.2f}")
                    print(f"Total P&L: ${state.get('total_pnl', 0):+,.2f}")
                    print(f"Trades: {state.get('total_trades', 0)}")
                    print(f"Win Rate: {state.get('win_rate', 0):.1f}%")
                    print(f"Max DD: {state.get('max_drawdown', 0):.1f}%")

                    if state.get('current_regimes'):
                        print(f"\nCurrent Regimes:")
                        for ticker, regime in state['current_regimes'].items():
                            print(f"  {ticker}: {regime}")

                    if state.get('regime_stats'):
                        print(f"\nRegime Performance:")
                        for ticker, stats in state['regime_stats'].items():
                            print(f"  {ticker}:")
                            for regime, data in stats.items():
                                wr = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
                                print(f"    {regime}: {data['trades']}t, {wr:.0f}% WR, ${data['total_pnl']:+,.2f}")
                    print("=" * 60)
                    return
        except Exception as e:
            pass

        if status.get('active'):
            print(f"\nSession: {status['session_id']}")
            print(f"Capital: ${status['capital']:,.2f}")
            print(f"P&L: ${status['total_pnl']:+,.2f}")
            print(f"Trades: {status['total_trades']}")
            print(f"Win Rate: {status['win_rate']:.1f}%")
        else:
            print("\nNo active session. Run without --status to start.")
        return

    # Determine dynamic mode
    dynamic = not args.fixed

    # Run as daemon if requested
    if args.daemon:
        import subprocess
        cmd = [sys.executable, __file__,
               '--tickers'] + args.tickers + [
               '--interval', str(args.interval),
               '--hours', str(args.hours)]
        if not args.fixed:
            cmd.append('--dynamic')
        else:
            cmd.append('--fixed')

        # Start in background
        log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'forward_test.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        with open(log_path, 'a') as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        print(f"[DAEMON] Started forward test (PID: {process.pid})")
        print(f"[DAEMON] Tickers: {', '.join(args.tickers)}")
        print(f"[DAEMON] Mode: {'DYNAMIC' if dynamic else 'FIXED'}")
        print(f"[DAEMON] Log: {log_path}")
        print(f"\nTo check status: python {__file__} --status")
        print(f"To stop: kill {process.pid}")
        return

    runner = LiveForwardTestRunner(
        tickers=args.tickers,
        update_interval=args.interval,
        max_runtime_hours=args.hours,
        dynamic_strategy=dynamic,
        webhook_enabled=args.webhook,
        webhook_key=args.webhook_key,
        api_base_url=args.api_url,
        no_projectx=args.no_projectx
    )

    # Print webhook status
    if args.webhook:
        print(f"\n[WEBHOOK] Signal generation ENABLED")
        if args.webhook_key:
            print(f"[WEBHOOK] Using key: {args.webhook_key[:8]}...")
        else:
            print(f"[WEBHOOK] Using key from SMARTFLOW_WEBHOOK_KEY env var")
        print(f"[WEBHOOK] API URL: {args.api_url or os.getenv('API_BASE_URL', 'http://localhost:8000')}")
    else:
        print(f"\n[WEBHOOK] Signal generation DISABLED (use --webhook to enable)")

    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
