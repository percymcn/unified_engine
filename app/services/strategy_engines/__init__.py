"""
SmartFlow Strategy Engines
===========================

Four core strategy engines for systematic trading:

1. BREAKOUT ENGINE (breakout_v1)
   - Compression + structural level breakouts
   - Volume expansion confirmation
   - Target: Next structural level or 2-3 ATR

2. TREND ENGINE (trend_v1)
   - Pullback entries in sustained trends
   - EMA/VWAP zone entries
   - Target: Continuation to trend extreme

3. MEAN REVERSION ENGINE (mean_reversion_v1)
   - Return to fair value in ranges
   - Bollinger/RSI extremes
   - Target: VWAP reclaim

4. LIQUIDITY REVERSAL ENGINE (liquidity_reversal_v1)
   - False breakout detection
   - Stop hunt identification
   - Target: Opposite side of range

All engines implement the StrategyEngine interface and integrate with:
- SmartFlow backtest system
- Strategy registry
- Portfolio allocator
- Router
"""

from app.services.strategy_engines.base import (
    StrategyEngine,
    SignalContext,
    TradingSignal
)

from app.services.strategy_engines.breakout import (
    BreakoutEngine,
    get_breakout_engine
)

from app.services.strategy_engines.trend import (
    TrendEngine,
    get_trend_engine
)

from app.services.strategy_engines.mean_reversion import (
    MeanReversionEngine,
    get_mean_reversion_engine
)

from app.services.strategy_engines.liquidity_reversal import (
    LiquidityReversalEngine,
    get_liquidity_reversal_engine
)

# Engine registry
ENGINE_TYPES = {
    'breakout': BreakoutEngine,
    'trend': TrendEngine,
    'mean_reversion': MeanReversionEngine,
    'liquidity_reversal': LiquidityReversalEngine
}

# Default strategy IDs
DEFAULT_STRATEGY_IDS = {
    'breakout': 'breakout_v1',
    'trend': 'trend_v1',
    'mean_reversion': 'mean_reversion_v1',
    'liquidity_reversal': 'liquidity_reversal_v1'
}


def get_engine(strategy_type: str, strategy_id: str = None) -> StrategyEngine:
    """
    Get strategy engine by type.

    Args:
        strategy_type: One of 'breakout', 'trend', 'mean_reversion', 'liquidity_reversal'
        strategy_id: Optional strategy ID (defaults to {type}_v1)

    Returns:
        StrategyEngine instance

    Raises:
        ValueError: If strategy_type is unknown
    """
    if strategy_type not in ENGINE_TYPES:
        raise ValueError(
            f"Unknown strategy type: {strategy_type}. "
            f"Must be one of {list(ENGINE_TYPES.keys())}"
        )

    engine_class = ENGINE_TYPES[strategy_type]

    # Use default strategy_id if not provided
    if strategy_id is None:
        strategy_id = DEFAULT_STRATEGY_IDS[strategy_type]

    return engine_class(strategy_id)


def get_all_engines():
    """
    Get all strategy engines with default IDs.

    Returns:
        Dict mapping strategy_type to engine instance
    """
    return {
        'breakout': get_breakout_engine(),
        'trend': get_trend_engine(),
        'mean_reversion': get_mean_reversion_engine(),
        'liquidity_reversal': get_liquidity_reversal_engine()
    }


__all__ = [
    # Base classes
    'StrategyEngine',
    'SignalContext',
    'TradingSignal',

    # Engine classes
    'BreakoutEngine',
    'TrendEngine',
    'MeanReversionEngine',
    'LiquidityReversalEngine',

    # Factory functions
    'get_breakout_engine',
    'get_trend_engine',
    'get_mean_reversion_engine',
    'get_liquidity_reversal_engine',
    'get_engine',
    'get_all_engines',

    # Constants
    'ENGINE_TYPES',
    'DEFAULT_STRATEGY_IDS',
]
