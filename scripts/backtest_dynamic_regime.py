#!/usr/bin/env python3
"""
Dynamic Regime Strategy Backtest
=================================

1. Registers the dynamic_regime_v1 strategy in the database
2. Runs backtest across all instruments
3. Reports results with regime breakdown

Instruments:
- Crypto: BTCUSD, ETHUSD
- Indices/Futures: US30, NAS100, SPX500
- Forex: USDJPY, GBPJPY
- Commodities: XAUUSD

Usage:
    python scripts/backtest_dynamic_regime.py
    python scripts/backtest_dynamic_regime.py --days 30
    python scripts/backtest_dynamic_regime.py --tickers BTCUSD ETHUSD
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('DynamicRegimeBacktest')

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Imports
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.strategy_registry_models import SmartFlowStrategy
from app.services.strategy_registry.schemas import StrategyStatus, StrategyType
from app.services.strategy_engines.dynamic_regime import DynamicRegimeEngine, get_dynamic_regime_engine
from app.services.strategy_engines.base import SignalContext, TradingSignal

# Data sources
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("ccxt not available - crypto backtest disabled")

try:
    from polygon import RESTClient as PolygonClient
    POLYGON_AVAILABLE = True
except ImportError:
    POLYGON_AVAILABLE = False
    logger.warning("polygon not available - stocks/forex backtest limited")

import pandas as pd
import numpy as np

# All instruments to backtest
ALL_INSTRUMENTS = [
    # Crypto (24/7 - best for testing)
    {"ticker": "BTCUSD", "source": "kraken", "type": "crypto"},
    {"ticker": "ETHUSD", "source": "kraken", "type": "crypto"},
    # Indices/Futures CFD proxies
    {"ticker": "US30", "source": "polygon", "polygon_symbol": "DIA", "type": "index"},
    {"ticker": "NAS100", "source": "polygon", "polygon_symbol": "QQQ", "type": "index"},
    {"ticker": "SPX500", "source": "polygon", "polygon_symbol": "SPY", "type": "index"},
    # Forex
    {"ticker": "USDJPY", "source": "polygon", "type": "forex"},
    {"ticker": "GBPJPY", "source": "polygon", "type": "forex"},
    # Commodities
    {"ticker": "XAUUSD", "source": "polygon", "polygon_symbol": "GLD", "type": "commodity"},
]


@dataclass
class BacktestResult:
    """Result for a single instrument backtest."""
    ticker: str
    source: str
    start_date: str
    end_date: str
    total_bars: int

    # Signals
    total_signals: int
    long_signals: int
    short_signals: int

    # Performance
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # P&L
    gross_profit: float
    gross_loss: float
    net_pnl: float
    net_pnl_pct: float

    # Risk metrics
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float

    # Regime breakdown
    regime_stats: Dict[str, Dict]

    # Errors
    errors: List[str]


class DynamicRegimeBacktester:
    """Backtester for Dynamic Regime Strategy."""

    def __init__(self, days: int = 30):
        self.days = days
        self.engine = get_dynamic_regime_engine("dynamic_regime_v1")

        # Initialize data sources
        self.kraken = None
        if CCXT_AVAILABLE:
            self.kraken = ccxt.kraken({
                'enableRateLimit': True
            })

        self.polygon_key = os.getenv('POLYGON_API_KEY')
        self.polygon = None
        if POLYGON_AVAILABLE and self.polygon_key:
            self.polygon = PolygonClient(self.polygon_key)

        # Results storage
        self.results: Dict[str, BacktestResult] = {}
        self.all_trades: List[Dict] = []

    async def fetch_crypto_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch crypto data from Kraken."""
        if not self.kraken:
            return None

        try:
            symbol = f"{ticker[:3]}/{ticker[3:]}"  # BTCUSD -> BTC/USD

            # Fetch OHLCV data
            since = int((datetime.now() - timedelta(days=self.days)).timestamp() * 1000)
            ohlcv = self.kraken.fetch_ohlcv(symbol, '5m', since=since, limit=1000)

            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.info(f"Fetched {len(df)} bars for {ticker} from Kraken")
            return df

        except Exception as e:
            logger.error(f"Error fetching {ticker} from Kraken: {e}")
            return None

    async def fetch_polygon_data(self, ticker: str, polygon_symbol: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Fetch stock/forex data from Polygon."""
        if not self.polygon:
            return None

        try:
            symbol = polygon_symbol or ticker
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.days)

            # Use aggregates for 5-minute bars
            aggs = self.polygon.get_aggs(
                symbol,
                5,
                "minute",
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                limit=50000
            )

            if not aggs:
                return None

            data = []
            for agg in aggs:
                data.append({
                    'timestamp': pd.to_datetime(agg.timestamp, unit='ms'),
                    'open': agg.open,
                    'high': agg.high,
                    'low': agg.low,
                    'close': agg.close,
                    'volume': agg.volume
                })

            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)

            logger.info(f"Fetched {len(df)} bars for {ticker} ({symbol}) from Polygon")
            return df

        except Exception as e:
            logger.error(f"Error fetching {ticker} from Polygon: {e}")
            return None

    async def fetch_data(self, instrument: Dict) -> Optional[pd.DataFrame]:
        """Fetch data for an instrument."""
        ticker = instrument["ticker"]
        source = instrument["source"]

        if source == "kraken":
            return await self.fetch_crypto_data(ticker)
        elif source == "polygon":
            polygon_symbol = instrument.get("polygon_symbol")
            return await self.fetch_polygon_data(ticker, polygon_symbol)

        return None

    def run_backtest(self, ticker: str, df: pd.DataFrame) -> BacktestResult:
        """Run backtest on a single instrument."""
        errors = []

        # Initialize tracking
        trades = []
        position = None  # Current position
        equity_curve = [10000.0]  # Starting equity

        total_signals = 0
        long_signals = 0
        short_signals = 0

        regime_stats = {
            'trending_up': {'signals': 0, 'wins': 0, 'pnl': 0.0},
            'trending_down': {'signals': 0, 'wins': 0, 'pnl': 0.0},
            'ranging': {'signals': 0, 'wins': 0, 'pnl': 0.0},
            'volatile': {'signals': 0, 'wins': 0, 'pnl': 0.0},
            'breakout': {'signals': 0, 'wins': 0, 'pnl': 0.0},
            'neutral': {'signals': 0, 'wins': 0, 'pnl': 0.0},
        }

        # Walk through data
        for i in range(50, len(df)):  # Need 50 bars for indicators
            bar = df.iloc[i]
            historical_df = df.iloc[max(0, i-200):i+1].copy()  # Last 200 bars

            # Create signal context
            context = SignalContext(
                ticker=ticker,
                timestamp=historical_df.index[-1] if hasattr(historical_df.index, '__getitem__') else datetime.now(),
                df=historical_df,
                close=bar['close'],
                high=bar['high'],
                low=bar['low'],
                open=bar['open'],
                volume=bar['volume']
            )

            # Generate signal
            try:
                signal = self.engine.generate_signal(context)
            except Exception as e:
                errors.append(f"Signal error at bar {i}: {str(e)}")
                continue

            regime = signal.regime or 'neutral'

            # Check for exit first (if in position)
            if position:
                should_exit = False
                exit_reason = ""
                exit_pnl = 0.0

                if position['direction'] == 'long':
                    # Check stop loss
                    if bar['low'] <= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                        exit_price = position['stop_loss']
                    # Check take profit
                    elif bar['high'] >= position['take_profit']:
                        should_exit = True
                        exit_reason = "take_profit"
                        exit_price = position['take_profit']
                else:  # short
                    if bar['high'] >= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                        exit_price = position['stop_loss']
                    elif bar['low'] <= position['take_profit']:
                        should_exit = True
                        exit_reason = "take_profit"
                        exit_price = position['take_profit']

                if should_exit:
                    # Calculate P&L
                    if position['direction'] == 'long':
                        exit_pnl = (exit_price - position['entry_price']) / position['entry_price'] * 100
                    else:
                        exit_pnl = (position['entry_price'] - exit_price) / position['entry_price'] * 100

                    # Adjust for position size
                    exit_pnl *= position.get('size_mult', 1.0)

                    is_win = exit_pnl > 0

                    trade = {
                        'ticker': ticker,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'entry_time': position['entry_time'],
                        'exit_time': bar.name if hasattr(bar, 'name') else datetime.now(),
                        'pnl_pct': exit_pnl,
                        'regime': position['regime'],
                        'exit_reason': exit_reason,
                        'is_win': is_win
                    }
                    trades.append(trade)

                    # Update equity
                    equity_curve.append(equity_curve[-1] * (1 + exit_pnl / 100))

                    # Update regime stats
                    pos_regime = position['regime']
                    if pos_regime in regime_stats:
                        regime_stats[pos_regime]['pnl'] += exit_pnl
                        if is_win:
                            regime_stats[pos_regime]['wins'] += 1

                    position = None

            # Check for new entry (if not in position)
            if not position and signal.direction in ['long', 'short']:
                total_signals += 1
                if signal.direction == 'long':
                    long_signals += 1
                else:
                    short_signals += 1

                # Track regime
                if regime in regime_stats:
                    regime_stats[regime]['signals'] += 1

                # Only take high-confidence signals
                if signal.confidence >= 0.55:
                    position = {
                        'direction': signal.direction,
                        'entry_price': bar['close'],
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'entry_time': bar.name if hasattr(bar, 'name') else datetime.now(),
                        'regime': regime,
                        'size_mult': signal.position_size_pct or 1.0
                    }

        # Close any open position at end
        if position:
            final_bar = df.iloc[-1]
            if position['direction'] == 'long':
                exit_pnl = (final_bar['close'] - position['entry_price']) / position['entry_price'] * 100
            else:
                exit_pnl = (position['entry_price'] - final_bar['close']) / position['entry_price'] * 100

            exit_pnl *= position.get('size_mult', 1.0)

            trade = {
                'ticker': ticker,
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': final_bar['close'],
                'entry_time': position['entry_time'],
                'exit_time': final_bar.name if hasattr(final_bar, 'name') else datetime.now(),
                'pnl_pct': exit_pnl,
                'regime': position['regime'],
                'exit_reason': 'end_of_data',
                'is_win': exit_pnl > 0
            }
            trades.append(trade)
            equity_curve.append(equity_curve[-1] * (1 + exit_pnl / 100))

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['is_win'])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0)
        gross_loss = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0))
        net_pnl = gross_profit - gross_loss

        # Final return
        final_equity = equity_curve[-1] if equity_curve else 10000.0
        net_pnl_pct = (final_equity - 10000.0) / 10000.0 * 100

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (annualized, assuming 5-min bars)
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                # Annualize: 252 days * 78 5-min bars per day
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 78)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)

        # Average win/loss
        wins = [t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]
        losses = [t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        # Calculate regime win rates
        for regime_name, stats in regime_stats.items():
            if stats['signals'] > 0:
                # Count trades in this regime
                regime_trades = [t for t in trades if t['regime'] == regime_name]
                if regime_trades:
                    stats['trades'] = len(regime_trades)
                    stats['win_rate'] = sum(1 for t in regime_trades if t['is_win']) / len(regime_trades)
                else:
                    stats['trades'] = 0
                    stats['win_rate'] = 0.0

        # Store trades globally
        self.all_trades.extend(trades)

        return BacktestResult(
            ticker=ticker,
            source="backtest",
            start_date=str(df.index[0]) if len(df) > 0 else "",
            end_date=str(df.index[-1]) if len(df) > 0 else "",
            total_bars=len(df),
            total_signals=total_signals,
            long_signals=long_signals,
            short_signals=short_signals,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net_pnl,
            net_pnl_pct=net_pnl_pct,
            max_drawdown_pct=max_dd,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            regime_stats=regime_stats,
            errors=errors
        )

    async def run_all_backtests(self, instruments: List[Dict]) -> Dict[str, BacktestResult]:
        """Run backtests for all instruments."""
        for instrument in instruments:
            ticker = instrument["ticker"]
            logger.info(f"\n{'='*50}")
            logger.info(f"Backtesting {ticker}...")
            logger.info(f"{'='*50}")

            # Fetch data
            df = await self.fetch_data(instrument)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {ticker} - skipping")
                self.results[ticker] = BacktestResult(
                    ticker=ticker,
                    source=instrument["source"],
                    start_date="",
                    end_date="",
                    total_bars=0,
                    total_signals=0,
                    long_signals=0,
                    short_signals=0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    gross_profit=0.0,
                    gross_loss=0.0,
                    net_pnl=0.0,
                    net_pnl_pct=0.0,
                    max_drawdown_pct=0.0,
                    sharpe_ratio=0.0,
                    profit_factor=0.0,
                    avg_win=0.0,
                    avg_loss=0.0,
                    regime_stats={},
                    errors=["Insufficient data"]
                )
                continue

            # Run backtest
            result = self.run_backtest(ticker, df)
            self.results[ticker] = result

            # Print summary
            logger.info(f"\n{ticker} Results:")
            logger.info(f"  Bars: {result.total_bars}")
            logger.info(f"  Signals: {result.total_signals} (L:{result.long_signals}, S:{result.short_signals})")
            logger.info(f"  Trades: {result.total_trades}")
            logger.info(f"  Win Rate: {result.win_rate:.1%}")
            logger.info(f"  Net P&L: {result.net_pnl_pct:.2f}%")
            logger.info(f"  Max DD: {result.max_drawdown_pct:.2f}%")
            logger.info(f"  Sharpe: {result.sharpe_ratio:.2f}")
            logger.info(f"  Profit Factor: {result.profit_factor:.2f}")

            # Small delay to respect rate limits
            await asyncio.sleep(0.5)

        return self.results

    def print_summary(self):
        """Print overall backtest summary."""
        print("\n" + "="*80)
        print("DYNAMIC REGIME STRATEGY BACKTEST SUMMARY")
        print("="*80)

        # Aggregate metrics
        total_trades = sum(r.total_trades for r in self.results.values())
        total_wins = sum(r.winning_trades for r in self.results.values())
        total_pnl = sum(r.net_pnl for r in self.results.values())

        avg_win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        avg_sharpe = np.mean([r.sharpe_ratio for r in self.results.values() if r.total_trades > 0])
        avg_pf = np.mean([r.profit_factor for r in self.results.values() if r.profit_factor < float('inf') and r.total_trades > 0])

        print(f"\nOverall Statistics:")
        print(f"  Instruments tested: {len(self.results)}")
        print(f"  Total trades: {total_trades}")
        print(f"  Overall win rate: {avg_win_rate:.1%}")
        print(f"  Total P&L: {total_pnl:.2f}%")
        print(f"  Avg Sharpe: {avg_sharpe:.2f}")
        print(f"  Avg Profit Factor: {avg_pf:.2f}")

        # Per-instrument table
        print(f"\n{'Ticker':<12} {'Trades':>8} {'Win Rate':>10} {'Net P&L':>10} {'Max DD':>10} {'Sharpe':>8} {'PF':>8}")
        print("-"*70)

        for ticker, result in sorted(self.results.items()):
            pf_str = f"{result.profit_factor:.2f}" if result.profit_factor < float('inf') else "∞"
            print(f"{ticker:<12} {result.total_trades:>8} {result.win_rate:>10.1%} {result.net_pnl_pct:>10.2f}% {result.max_drawdown_pct:>9.2f}% {result.sharpe_ratio:>8.2f} {pf_str:>8}")

        # Aggregate regime stats
        print(f"\nRegime Breakdown (All Instruments):")
        print(f"{'Regime':<15} {'Signals':>10} {'Trades':>10} {'Win Rate':>10} {'P&L':>12}")
        print("-"*60)

        regime_totals = {}
        for result in self.results.values():
            for regime, stats in result.regime_stats.items():
                if regime not in regime_totals:
                    regime_totals[regime] = {'signals': 0, 'trades': 0, 'wins': 0, 'pnl': 0.0}
                regime_totals[regime]['signals'] += stats.get('signals', 0)
                regime_totals[regime]['trades'] += stats.get('trades', 0)
                regime_totals[regime]['wins'] += stats.get('wins', 0)
                regime_totals[regime]['pnl'] += stats.get('pnl', 0.0)

        for regime, stats in sorted(regime_totals.items(), key=lambda x: x[1]['signals'], reverse=True):
            wr = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0.0
            print(f"{regime:<15} {stats['signals']:>10} {stats['trades']:>10} {wr:>10.1%} {stats['pnl']:>12.2f}%")

        print("\n" + "="*80)

    def export_results(self, filename: str):
        """Export results to JSON."""
        export_data = {
            'strategy': 'dynamic_regime_v1',
            'backtest_days': self.days,
            'run_date': datetime.now().isoformat(),
            'summary': {
                'total_instruments': len(self.results),
                'total_trades': sum(r.total_trades for r in self.results.values()),
                'overall_pnl_pct': sum(r.net_pnl_pct for r in self.results.values())
            },
            'instruments': {ticker: asdict(result) for ticker, result in self.results.items()},
            'trades': self.all_trades
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Results exported to {filename}")


def register_dynamic_regime_strategy(db: Session) -> bool:
    """Register the Dynamic Regime strategy in the database."""
    strategy_id = "dynamic_regime_v1"

    # Check if exists
    existing = db.query(SmartFlowStrategy).filter(SmartFlowStrategy.strategy_id == strategy_id).first()

    engine_data = {
        "strategy_id": "dynamic_regime_v1",
        "strategy_type": "dynamic_regime",
        "version": "1.0.0",
        "status": StrategyStatus.CANDIDATE.value,  # Start as candidate until backtest proves it
        "parameters": {
            "trending_threshold": 3.0,
            "ranging_threshold": 1.0,
            "volatile_threshold": 5.0,
            "compression_atr_ratio": 0.6,
            "regimes": {
                "trending_up": {"stop_pct": 2.0, "target_pct": 2.0, "size_mult": 1.0},
                "trending_down": {"stop_pct": 2.0, "target_pct": 2.0, "size_mult": 1.0},
                "ranging": {"stop_pct": 1.0, "target_pct": 1.0, "size_mult": 0.75},
                "volatile": {"stop_pct": 1.5, "target_pct": 2.5, "size_mult": 0.5},
                "breakout": {"stop_pct": 2.5, "target_pct": 3.0, "size_mult": 1.25},
                "neutral": {"stop_pct": 1.5, "target_pct": 1.5, "size_mult": 0.75}
            },
            "max_pyramid_levels": 3,
            "pyramid_pullback_pct": 0.5,
            "ema_fast": 9,
            "ema_mid": 21,
            "ema_slow": 50,
            "rsi_period": 14,
            "atr_period": 14
        },
        "hypothesis": (
            "Adaptive multi-regime strategy that automatically adjusts trading parameters "
            "based on real-time market regime detection. Uses percentage-based stops/targets "
            "that adapt to trending (2%/2%), ranging (1%/1%), volatile (1.5%/2.5%), "
            "and breakout (2.5%/3%) conditions. Includes pyramid add-on logic (max 3 levels, "
            "50% pullback + 2 bars continuation). Based on run_live_forward_test.py."
        )
    }

    if existing:
        print(f"Updating existing strategy: {strategy_id}")
        existing.parameters = engine_data["parameters"]
        existing.version = engine_data["version"]
        existing.status = engine_data["status"]
        existing.hypothesis = engine_data["hypothesis"]
    else:
        print(f"Creating new strategy: {strategy_id}")
        new_strategy = SmartFlowStrategy(
            strategy_id=strategy_id,
            strategy_type=engine_data["strategy_type"],
            version=engine_data["version"],
            status=engine_data["status"],
            parameters=engine_data["parameters"],
            hypothesis=engine_data["hypothesis"],
            parent_strategy_id=None,
            family_id="dynamic_regime",
            generation=0,
        )
        db.add(new_strategy)

    db.commit()
    print(f"✅ Strategy {strategy_id} registered successfully")
    return True


async def main():
    parser = argparse.ArgumentParser(description="Dynamic Regime Strategy Backtest")
    parser.add_argument('--days', type=int, default=30, help='Number of days to backtest')
    parser.add_argument('--tickers', nargs='+', help='Specific tickers to test')
    parser.add_argument('--register-only', action='store_true', help='Only register strategy, skip backtest')
    parser.add_argument('--skip-register', action='store_true', help='Skip strategy registration')
    parser.add_argument('--output', type=str, default='dynamic_regime_backtest.json', help='Output file')

    args = parser.parse_args()

    # Register strategy
    if not args.skip_register:
        print("\n" + "="*60)
        print("REGISTERING DYNAMIC REGIME STRATEGY")
        print("="*60)

        db = SessionLocal()
        try:
            register_dynamic_regime_strategy(db)
        finally:
            db.close()

    if args.register_only:
        print("\n✅ Registration complete. Skipping backtest.")
        return

    # Filter instruments if specific tickers requested
    instruments = ALL_INSTRUMENTS
    if args.tickers:
        instruments = [i for i in ALL_INSTRUMENTS if i["ticker"] in args.tickers]
        if not instruments:
            print(f"No matching instruments for: {args.tickers}")
            print(f"Available: {[i['ticker'] for i in ALL_INSTRUMENTS]}")
            return

    # Run backtest
    print("\n" + "="*60)
    print(f"RUNNING BACKTEST ({args.days} days)")
    print("="*60)

    backtester = DynamicRegimeBacktester(days=args.days)
    await backtester.run_all_backtests(instruments)

    # Print summary
    backtester.print_summary()

    # Export results
    backtester.export_results(args.output)

    # Update strategy with backtest metrics if successful
    if not args.skip_register and backtester.results:
        db = SessionLocal()
        try:
            strategy = db.query(SmartFlowStrategy).filter(SmartFlowStrategy.strategy_id == "dynamic_regime_v1").first()
            if strategy:
                total_trades = sum(r.total_trades for r in backtester.results.values())
                total_wins = sum(r.winning_trades for r in backtester.results.values())

                strategy.total_return_pct = sum(r.net_pnl_pct for r in backtester.results.values())
                strategy.win_rate = total_wins / total_trades if total_trades > 0 else 0.0
                strategy.sharpe_ratio = np.mean([r.sharpe_ratio for r in backtester.results.values() if r.total_trades > 0])
                strategy.max_drawdown = max(r.max_drawdown_pct for r in backtester.results.values())
                strategy.total_trades = total_trades

                # Promote to approved if metrics are good
                if strategy.win_rate >= 0.5 and strategy.sharpe_ratio >= 0.5:
                    strategy.status = StrategyStatus.APPROVED_FOR_ROUTER.value
                    print(f"\n✅ Strategy promoted to APPROVED_FOR_ROUTER based on backtest results")

                db.commit()
                print(f"✅ Strategy metrics updated in database")
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(main())
