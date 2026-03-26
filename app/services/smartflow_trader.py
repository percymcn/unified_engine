"""
SmartFlow Autonomous Trader
===========================

Runs SmartFlow analysis, applies guardrail risk checks, and executes trades
via the existing webhook_execute pipeline.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional

from app.db.database import SessionLocal
from app.models.database_models import WebhookConfig
from app.services.market_data_service import MarketDataService
from app.services.risk_manager import GuardrailRiskManager, GuardrailConfig
from app.services.smartflow_service import SmartFlowService
from app.services.trade_journal import TradeJournal

logger = logging.getLogger(__name__)


@dataclass
class TrackedTrade:
    """In-memory trade tracking for SmartFlow."""
    trade_id: Optional[int]
    symbol: str
    direction: str
    quantity: float
    entry_price: Optional[float]
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    strategy: Optional[str] = None
    status: str = "open"
    notes: Optional[str] = None


@dataclass
class SmartFlowTraderConfig:
    """Configuration for SmartFlowTrader."""
    paper_trading: bool = True
    cycle_interval_seconds: int = 60
    default_quantity: float = 1.0
    user_id: Optional[int] = None
    webhook_key: Optional[str] = None
    max_trades_to_keep: int = 500
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)


class FakeRequest:
    """Minimal request stub for execute_tradingview_signal."""
    def __init__(self, payload: dict):
        self._payload = payload
        self.client = SimpleNamespace(host="smartflow-trader")
        self.headers = {"user-agent": "smartflow-trader"}

    async def json(self):
        return self._payload


class SmartFlowTrader:
    """Autonomous SmartFlow trading engine."""

    def __init__(self, config: Optional[SmartFlowTraderConfig] = None):
        self.config = config or SmartFlowTraderConfig()
        self.trades: List[TrackedTrade] = []
        self.open_trades: Dict[str, TrackedTrade] = {}
        self.last_signal_timestamps: Dict[str, datetime] = {}

        self.market_data = MarketDataService()
        self.trade_journal = TradeJournal()
        self.risk_manager = GuardrailRiskManager(self.config.guardrails)

        # Use a dedicated SmartFlowService instance to avoid impacting existing loops.
        self.signal_engine = SmartFlowService()
        self.signal_engine.enabled = True
        self.signal_engine.webhook_urls = []

        self._load_webhook_key()

        logger.info(
            "SmartFlowTrader initialized (paper_trading=%s, interval=%ss)",
            self.config.paper_trading,
            self.config.cycle_interval_seconds,
        )

    def _load_webhook_key(self) -> None:
        """Load webhook key from configuration or database."""
        if self.config.webhook_key:
            return

        db = SessionLocal()
        try:
            webhook = db.query(WebhookConfig).filter(
                WebhookConfig.source == "smartflow",
                WebhookConfig.is_active == True
            ).first()
            if webhook:
                self.config.webhook_key = webhook.webhook_key
                self.config.user_id = self.config.user_id or webhook.user_id
        except Exception as exc:
            logger.error(f"Failed to load SmartFlow webhook config: {exc}")
        finally:
            db.close()

    async def _get_latest_price(self, symbol: str) -> Optional[float]:
        try:
            quote = await self.market_data.get_realtime_quote(symbol)
            if quote:
                return quote.last_price
        except Exception as exc:
            logger.debug(f"Price fetch error for {symbol}: {exc}")
        return None

    def _collect_new_signals(self) -> List:
        new_signals = []
        for ticker, signal in self.signal_engine.last_signal.items():
            last_seen = self.last_signal_timestamps.get(ticker)
            if not last_seen or (signal.timestamp and signal.timestamp > last_seen):
                if signal.timestamp:
                    self.last_signal_timestamps[ticker] = signal.timestamp
                new_signals.append(signal)
        return new_signals

    def _resolve_strategy_id(self) -> Optional[str]:
        allocation = getattr(self.signal_engine, "_current_allocation_decision", None)
        if not allocation or not allocation.selected_strategies:
            return None
        top = max(allocation.selected_strategies, key=lambda s: s.allocation_weight)
        return top.strategy_id

    async def _execute_via_webhook(self, payload: dict) -> bool:
        if not self.config.webhook_key:
            logger.warning("No SmartFlow webhook_key configured; skipping execution")
            return False

        from app.routers.webhook_execute import execute_tradingview_signal

        request = FakeRequest(payload)
        db = SessionLocal()
        try:
            await execute_tradingview_signal(request=request, db=db)
            return True
        except Exception as exc:
            logger.error(f"Webhook execution failed: {exc}")
            return False
        finally:
            db.close()

    async def _handle_entry(self, signal) -> None:
        quantity = self.config.default_quantity
        allowed, reason = self.risk_manager.check_trade_allowed(signal.ticker, quantity)
        if not allowed:
            logger.info(f"Trade blocked by guardrails: {signal.ticker} {signal.action} - {reason}")
            return

        entry_price = signal.price or await self._get_latest_price(signal.ticker)
        strategy_id = self._resolve_strategy_id()
        notes = signal.reason or "SmartFlow signal"

        trade_id = self.trade_journal.log_entry(
            user_id=self.config.user_id,
            symbol=signal.ticker,
            direction=signal.action,
            quantity=quantity,
            entry_price=entry_price,
            strategy=strategy_id,
            status="paper_open" if self.config.paper_trading else "open",
            notes=notes,
        )

        tracked = TrackedTrade(
            trade_id=trade_id,
            symbol=signal.ticker,
            direction=signal.action,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.utcnow(),
            strategy=strategy_id,
            status="paper_open" if self.config.paper_trading else "open",
            notes=notes,
        )
        self.trades.append(tracked)
        self.open_trades[signal.ticker] = tracked
        self.risk_manager.record_trade_open(trade_id, signal.ticker, quantity)

        if len(self.trades) > self.config.max_trades_to_keep:
            self.trades = self.trades[-self.config.max_trades_to_keep:]

        if self.config.paper_trading:
            logger.info(f"🧪 Paper trade logged: {signal.ticker} {signal.action} qty={quantity}")
            return

        payload = {
            "webhook_key": self.config.webhook_key,
            "action": signal.action,
            "symbol": signal.ticker,
            "quantity": quantity,
            "price": entry_price,
            "strategy_id": strategy_id,
            "comment": "SmartFlow autonomous trade",
        }
        await self._execute_via_webhook(payload)

    @staticmethod
    def _calculate_unrealized_pct(direction: str, entry_price: float, current_price: float) -> Optional[float]:
        if entry_price <= 0:
            return None
        if direction == "buy":
            return (current_price - entry_price) / entry_price
        if direction == "sell":
            return (entry_price - current_price) / entry_price
        return None

    def _calculate_pnl(self, trade: TrackedTrade, exit_price: Optional[float]) -> Optional[float]:
        if trade.entry_price is None or exit_price is None:
            return None
        if trade.direction == "buy":
            return (exit_price - trade.entry_price) * trade.quantity
        if trade.direction == "sell":
            return (trade.entry_price - exit_price) * trade.quantity
        return None

    async def _close_trade(self, trade: TrackedTrade, exit_price: Optional[float], reason: str) -> None:
        pnl = self._calculate_pnl(trade, exit_price)
        trade.exit_price = exit_price
        trade.exit_time = datetime.utcnow()
        trade.pnl = pnl
        trade.status = "paper_closed" if self.config.paper_trading else "closed"
        if reason:
            trade.notes = reason

        self.risk_manager.record_trade_close(trade.symbol, pnl or 0.0)
        if trade.trade_id:
            self.trade_journal.close_trade(
                trade_id=trade.trade_id,
                exit_price=exit_price,
                exit_time=trade.exit_time,
                pnl=pnl,
                status=trade.status,
                notes=reason,
            )

        self.open_trades.pop(trade.symbol, None)

        if self.config.paper_trading:
            logger.info(f"🧪 Paper trade closed: {trade.symbol} pnl={pnl} reason={reason}")
            return

        payload = {
            "webhook_key": self.config.webhook_key,
            "action": "close",
            "symbol": trade.symbol,
            "quantity": trade.quantity,
            "price": exit_price,
            "strategy_id": trade.strategy,
            "comment": f"SmartFlow autonomous close ({reason})",
        }
        await self._execute_via_webhook(payload)

    async def _handle_close(self, signal) -> None:
        open_trade = self.open_trades.get(signal.ticker)
        if not open_trade:
            logger.info(f"No open trade to close for {signal.ticker}")
            return

        exit_price = signal.price or await self._get_latest_price(signal.ticker)
        await self._close_trade(open_trade, exit_price, "close_signal")

    async def _check_exit_conditions(self) -> None:
        for symbol, trade in list(self.open_trades.items()):
            if trade.entry_price is None:
                continue
            current_price = await self._get_latest_price(symbol)
            if current_price is None:
                continue
            unrealized_pct = self._calculate_unrealized_pct(
                trade.direction,
                trade.entry_price,
                current_price,
            )
            if unrealized_pct is None:
                continue
            if unrealized_pct > 0.02:
                await self._close_trade(trade, current_price, "take_profit_2pct")
            elif unrealized_pct < -0.01:
                await self._close_trade(trade, current_price, "stop_loss_1pct")

    async def run_cycle(self) -> None:
        """Run one analysis + execution cycle."""
        await self.signal_engine.run_cycle()
        await self._check_exit_conditions()
        for signal in self._collect_new_signals():
            if signal.action in ("buy", "sell"):
                open_trade = self.open_trades.get(signal.ticker)
                if open_trade and open_trade.direction != signal.action:
                    exit_price = signal.price or await self._get_latest_price(signal.ticker)
                    await self._close_trade(open_trade, exit_price, "opposite_signal")
                await self._handle_entry(signal)
            elif signal.action == "close":
                await self._handle_close(signal)

    async def run_forever(self) -> None:
        """Run SmartFlowTrader continuously."""
        while True:
            try:
                await self.run_cycle()
            except Exception as exc:
                logger.error(f"SmartFlowTrader cycle error: {exc}", exc_info=True)
            await asyncio.sleep(self.config.cycle_interval_seconds)


_smartflow_trader: Optional[SmartFlowTrader] = None


def get_smartflow_trader() -> SmartFlowTrader:
    """Get or create the singleton SmartFlowTrader."""
    global _smartflow_trader
    if _smartflow_trader is None:
        _smartflow_trader = SmartFlowTrader()
    return _smartflow_trader


async def smartflow_trader_background_loop() -> None:
    """Background task entry for SmartFlowTrader."""
    trader = get_smartflow_trader()
    await trader.run_forever()
