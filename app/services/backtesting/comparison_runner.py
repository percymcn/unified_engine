"""
Backtest Comparison Service
============================

Runs multiple engines side-by-side under identical market conditions
and provides comparative analysis.

Phase 2B: Comparison Framework
- Multi-engine parallel execution
- Side-by-side performance metrics
- Regime-based performance breakdown
- Execution honesty tracking

IMPORTANT: Tracks whether each engine result uses true engine-specific
execution or falls back to unified strategy.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EngineExecutionMetadata:
    """Tracks execution honesty for each engine."""
    requested_engine_type: str
    actual_execution_mode: str  # e.g., 'deterministic_backtest', 'unified_fallback'
    unified_fallback_used: bool
    routing_status: str  # 'fully_routed', 'partially_routed', 'unified_fallback'
    notes: str = ""


@dataclass
class ComparisonResult:
    """Results from comparing multiple engines."""
    comparison_id: str
    timestamp: datetime

    # Inputs
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    engines_compared: List[str]

    # Per-engine results
    engine_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Per-engine execution metadata (Phase 2B honesty tracking)
    engine_metadata: Dict[str, EngineExecutionMetadata] = field(default_factory=dict)

    # Comparative metrics
    leaderboard: List[Dict[str, Any]] = field(default_factory=list)
    regime_comparison: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Warnings
    warnings: List[str] = field(default_factory=list)


class ComparisonRunner:
    """
    Runs multiple engine backtests in parallel and compares results.

    Phase 2B: Framework for engine comparison with execution honesty.
    """

    def __init__(self):
        self.active_comparisons: Dict[str, ComparisonResult] = {}
        logger.info("ComparisonRunner initialized")

    async def run_engine_comparison(
        self,
        ticker: str,
        days: int,
        engines: List[str],
        config_overrides: Optional[Dict] = None
    ) -> ComparisonResult:
        """
        Run multiple engines in parallel under identical conditions.

        Args:
            ticker: Symbol to backtest
            days: Days of history
            engines: List of engine types to compare
            config_overrides: Optional config parameters

        Returns:
            ComparisonResult with all engines' performance
        """
        comparison_id = f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting engine comparison {comparison_id}: {engines} on {ticker}")

        # Import here to avoid circular dependencies
        from app.services.smartflow_backtest import SmartFlowBacktester, BacktestConfig

        config = BacktestConfig()
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)

        # Run all engines in parallel
        tasks = []
        for engine_type in engines:
            tasks.append(self._run_single_engine(
                ticker=ticker,
                days=days,
                engine_type=engine_type,
                config=config
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build comparison result
        comparison = ComparisonResult(
            comparison_id=comparison_id,
            timestamp=datetime.now(),
            ticker=ticker,
            start_date="",  # Will be set from first result
            end_date="",
            initial_capital=config.initial_capital,
            engines_compared=engines
        )

        # Process each engine result
        for i, engine_type in enumerate(engines):
            result = results[i]

            if isinstance(result, Exception):
                logger.error(f"Engine {engine_type} failed: {result}")
                comparison.warnings.append(f"Engine {engine_type} failed: {str(result)}")
                continue

            metrics, metadata = result

            # Store results
            comparison.engine_results[engine_type] = asdict(metrics)
            comparison.engine_metadata[engine_type] = metadata

            # Set date range from first successful result
            if not comparison.start_date:
                comparison.start_date = metrics.start_date
                comparison.end_date = metrics.end_date

            # Add warning if using fallback
            if metadata.unified_fallback_used:
                comparison.warnings.append(
                    f"Engine '{engine_type}' used unified fallback strategy - results may not reflect true engine behavior"
                )

        # Build leaderboard
        comparison.leaderboard = self._build_leaderboard(comparison.engine_results)

        # Build regime comparison
        comparison.regime_comparison = self._build_regime_comparison(comparison.engine_results)

        # Store for retrieval
        self.active_comparisons[comparison_id] = comparison

        # Phase 4: Save to comparison store for data-driven routing
        try:
            from app.services.backtesting.comparison_store import get_comparison_store
            store = get_comparison_store()
            store.save_comparison_result(comparison)
            logger.info(f"Saved comparison {comparison_id} to store for router data")
        except Exception as e:
            logger.warning(f"Failed to save comparison to store: {e}")

        logger.info(f"Comparison {comparison_id} complete: {len(comparison.engine_results)} engines")

        return comparison

    async def _run_single_engine(
        self,
        ticker: str,
        days: int,
        engine_type: str,
        config: Any
    ) -> tuple:
        """
        Run a single engine backtest.

        Returns: (metrics, execution_metadata)
        """
        from app.services.smartflow_backtest import SmartFlowBacktester

        # Create backtester
        backtester = SmartFlowBacktester(config)

        # Determine execution mode
        execution_metadata = self._get_execution_metadata(engine_type)

        # Route to engine-specific backtest (Phase 2C + Phase 5A + Phase 5C)
        if engine_type == 'deterministic':
            logger.info(f"Routing {engine_type} to deterministic backtest path")
            metrics = await backtester.run_deterministic_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'quick':
            logger.info(f"Routing {engine_type} to quick backtest path")
            metrics = await backtester.run_quick_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'ai':
            # Phase 5A: AI-proxy backtest (NOT true Claude API)
            logger.info(f"Routing {engine_type} to AI-proxy backtest path")
            metrics = await backtester.run_ai_proxy_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'flow':
            # Phase 5B: Flow historical replay (TRUE historical Polygon data)
            logger.info(f"Routing {engine_type} to Flow historical replay path")
            metrics = await backtester.run_flow_backtest(
                ticker=ticker,
                days=days
            )
        # Phase 5C: 4 Specialized Strategy Engines (TRUE backtest paths)
        elif engine_type == 'breakout':
            logger.info(f"Routing {engine_type} to TRUE breakout backtest path")
            metrics = await backtester.run_breakout_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'trend':
            logger.info(f"Routing {engine_type} to TRUE trend backtest path")
            metrics = await backtester.run_trend_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'mean_reversion':
            logger.info(f"Routing {engine_type} to TRUE mean_reversion backtest path")
            metrics = await backtester.run_mean_reversion_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'liquidity_reversal':
            logger.info(f"Routing {engine_type} to TRUE liquidity_reversal backtest path")
            metrics = await backtester.run_liquidity_reversal_backtest(
                ticker=ticker,
                days=days
            )
        elif engine_type == 'pyramid':
            # Phase 5D: Pyramid dynamic strategy (2%/2% stops, pullback entries)
            logger.info(f"Routing {engine_type} to TRUE pyramid backtest path")
            metrics = await backtester.run_pyramid_backtest(
                ticker=ticker,
                days=days
            )
        else:
            # Unified - use default unified strategy
            metrics = await backtester.run_backtest(
                ticker=ticker,
                days=days
            )

        return (metrics, execution_metadata)

    def _get_execution_metadata(self, engine_type: str) -> EngineExecutionMetadata:
        """
        Determine execution mode for an engine type.

        Phase 2B: Tracks whether engine uses true implementation or fallback.
        """
        # Phase 2C + Phase 5C: Map engines to their actual execution status
        engine_routing_status = {
            'unified': {
                'mode': 'unified_strategy',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'Default unified strategy with regime detection'
            },
            'flow': {
                'mode': 'flow_historical_replay',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'Historical flow replay using real Polygon options trade data'
            },
            'ai': {
                'mode': 'ai_proxy_backtest',
                'fallback': False,
                'status': 'partially_routed',
                'notes': 'AI-proxy using MTF analysis + AI thresholds (not true Claude analysis)'
            },
            'deterministic': {
                'mode': 'deterministic_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'True multi-timeframe deterministic indicators (>=4/5 TFs, 75% confidence, 2:1 R:R)'
            },
            'quick': {
                'mode': 'quick_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'True 5m momentum quick mode (60% confidence, 1.5:1 R:R, 2hr max hold, volume-confirmed)'
            },
            # Phase 5C: 4 Specialized Strategy Engines (TRUE backtest paths)
            'breakout': {
                'mode': 'breakout_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'TRUE breakout engine: compression + structural level breakouts with volume expansion'
            },
            'trend': {
                'mode': 'trend_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'TRUE trend engine: EMA alignment pullback entries with structure stops'
            },
            'mean_reversion': {
                'mode': 'mean_reversion_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'TRUE mean reversion engine: Bollinger Band extremes with RSI confirmation'
            },
            'liquidity_reversal': {
                'mode': 'liquidity_reversal_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'TRUE liquidity reversal engine: equal high/low sweeps with rapid reversal'
            },
            # Phase 5D: Pyramid Dynamic Strategy
            'pyramid': {
                'mode': 'pyramid_backtest',
                'fallback': False,
                'status': 'fully_routed',
                'notes': 'TRUE pyramid engine: 2%/2% stops, pullback entries, max 3 positions, regime-adaptive sizing'
            }
        }

        engine_info = engine_routing_status.get(engine_type, engine_routing_status['unified'])

        return EngineExecutionMetadata(
            requested_engine_type=engine_type,
            actual_execution_mode=engine_info['mode'],
            unified_fallback_used=engine_info['fallback'],
            routing_status=engine_info['status'],
            notes=engine_info['notes']
        )

    def _build_leaderboard(self, engine_results: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """
        Build sorted leaderboard of engine performance.

        Sorts by Sharpe Ratio (primary), then Win Rate (secondary).
        """
        leaderboard = []

        for engine_type, metrics in engine_results.items():
            leaderboard.append({
                'engine': engine_type,
                'total_return_pct': metrics.get('total_return_pct', 0),
                'net_profit': metrics.get('net_profit', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'win_rate': metrics.get('win_rate', 0),
                'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
                'profit_factor': metrics.get('profit_factor', 0),
                'total_trades': metrics.get('total_trades', 0),
                'avg_trade': metrics.get('avg_trade', 0),
                'avg_holding_time_hours': metrics.get('avg_holding_time_hours', 0)
            })

        # Sort by Sharpe (descending), then Win Rate (descending)
        leaderboard.sort(
            key=lambda x: (x['sharpe_ratio'], x['win_rate']),
            reverse=True
        )

        # Add rank
        for i, entry in enumerate(leaderboard, 1):
            entry['rank'] = i

        return leaderboard

    def _build_regime_comparison(self, engine_results: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Build regime-based performance comparison.

        Returns: {
            'trending_up': {'flow': {...}, 'ai': {...}, ...},
            'trending_down': {...},
            ...
        }
        """
        regime_comparison = {}

        for engine_type, metrics in engine_results.items():
            regime_win_rates = metrics.get('regime_win_rates', {})
            regime_pnl = metrics.get('regime_pnl', {})

            for regime in regime_win_rates.keys():
                if regime not in regime_comparison:
                    regime_comparison[regime] = {}

                regime_comparison[regime][engine_type] = {
                    'win_rate': regime_win_rates.get(regime, 0),
                    'pnl': regime_pnl.get(regime, 0)
                }

        return regime_comparison

    def compare_backtest_runs(
        self,
        run_ids: List[str]
    ) -> Optional[ComparisonResult]:
        """
        Compare multiple saved backtest runs.

        Args:
            run_ids: List of comparison IDs to compare

        Returns:
            ComparisonResult combining the runs
        """
        # TODO: Implement saved run comparison
        logger.warning("Saved run comparison not yet implemented")
        return None

    def get_comparison(self, comparison_id: str) -> Optional[ComparisonResult]:
        """Get a stored comparison result."""
        return self.active_comparisons.get(comparison_id)

    def summarize_engine_performance(self, comparison: ComparisonResult) -> Dict[str, Any]:
        """
        Generate a summary of engine performance.

        Returns performance highlights and warnings.
        """
        summary = {
            'best_overall': None,
            'best_returns': None,
            'best_sharpe': None,
            'lowest_drawdown': None,
            'warnings': comparison.warnings,
            'execution_status': {}
        }

        if comparison.leaderboard:
            # Best overall (by rank)
            summary['best_overall'] = comparison.leaderboard[0]['engine']

            # Best returns
            best_return = max(
                comparison.leaderboard,
                key=lambda x: x['total_return_pct']
            )
            summary['best_returns'] = best_return['engine']

            # Best Sharpe
            best_sharpe = max(
                comparison.leaderboard,
                key=lambda x: x['sharpe_ratio']
            )
            summary['best_sharpe'] = best_sharpe['engine']

            # Lowest drawdown
            lowest_dd = min(
                comparison.leaderboard,
                key=lambda x: abs(x['max_drawdown_pct'])
            )
            summary['lowest_drawdown'] = lowest_dd['engine']

        # Execution status for each engine
        for engine, metadata in comparison.engine_metadata.items():
            summary['execution_status'][engine] = {
                'requested': metadata.requested_engine_type,
                'actual_mode': metadata.actual_execution_mode,
                'is_fallback': metadata.unified_fallback_used,
                'status': metadata.routing_status
            }

        return summary

    def summarize_regime_performance(self, comparison: ComparisonResult) -> Dict[str, Any]:
        """
        Generate regime performance summary.

        Returns which engine performs best in each regime.
        """
        regime_summary = {}

        for regime, engine_data in comparison.regime_comparison.items():
            if not engine_data:
                continue

            # Find best engine for this regime (by P&L)
            best_engine = max(
                engine_data.items(),
                key=lambda x: x[1].get('pnl', 0)
            )

            regime_summary[regime] = {
                'best_engine': best_engine[0],
                'best_pnl': best_engine[1].get('pnl', 0),
                'best_win_rate': best_engine[1].get('win_rate', 0)
            }

        return regime_summary


# Global instance
_comparison_runner: Optional[ComparisonRunner] = None

def get_comparison_runner() -> ComparisonRunner:
    """Get or create global comparison runner."""
    global _comparison_runner
    if _comparison_runner is None:
        _comparison_runner = ComparisonRunner()
    return _comparison_runner
