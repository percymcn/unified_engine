"""
Test script for Deterministic backtest implementation (Phase 2C).

Runs a quick comparison between Unified and Deterministic engines.
"""
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_deterministic_backtest():
    """Test Deterministic vs Unified comparison."""
    try:
        from app.services.backtesting.comparison_runner import get_comparison_runner

        logger.info("=" * 60)
        logger.info("Phase 2C: Testing Deterministic Backtest Implementation")
        logger.info("=" * 60)

        runner = get_comparison_runner()

        # Run comparison: Unified vs Deterministic
        logger.info("\nRunning comparison: unified vs deterministic")
        logger.info("Ticker: MES, Days: 30")

        comparison = await runner.run_engine_comparison(
            ticker='MES',
            days=30,
            engines=['unified', 'deterministic'],
            config_overrides={'initial_capital': 25000}
        )

        logger.info("\n" + "=" * 60)
        logger.info("COMPARISON RESULTS")
        logger.info("=" * 60)

        # Show execution metadata
        logger.info("\n--- Execution Metadata ---")
        for engine, metadata in comparison.engine_metadata.items():
            logger.info(f"\n{engine.upper()}:")
            logger.info(f"  Mode: {metadata.actual_execution_mode}")
            logger.info(f"  Fallback: {metadata.unified_fallback_used}")
            logger.info(f"  Status: {metadata.routing_status}")
            logger.info(f"  Notes: {metadata.notes}")

        # Show leaderboard
        logger.info("\n--- Performance Leaderboard ---")
        for entry in comparison.leaderboard:
            logger.info(
                f"\n#{entry['rank']} {entry['engine'].upper()}: "
                f"Return={entry['total_return_pct']:.2f}% | "
                f"Sharpe={entry['sharpe_ratio']:.2f} | "
                f"Win Rate={entry['win_rate']:.1f}% | "
                f"Trades={entry['total_trades']}"
            )

        # Show warnings
        if comparison.warnings:
            logger.info("\n--- Warnings ---")
            for warning in comparison.warnings:
                logger.warning(warning)
        else:
            logger.info("\n✅ No fallback warnings - true engine execution verified!")

        logger.info("\n" + "=" * 60)
        logger.info("TEST COMPLETE")
        logger.info("=" * 60)

        return comparison

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    result = asyncio.run(test_deterministic_backtest())
    sys.exit(0 if result else 1)
