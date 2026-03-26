"""
Phase 2C Complete Verification - All Three Engines
====================================================

Tests:
1. Unified vs Quick vs Deterministic (3-way comparison)
2. Verifies all engines are fully routed (no fallback)
3. Checks for real divergence in results
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


async def test_phase2c_complete():
    """Test all three engines: Unified, Deterministic, Quick."""
    try:
        from app.services.backtesting.comparison_runner import get_comparison_runner

        logger.info("=" * 80)
        logger.info("PHASE 2C COMPLETE VERIFICATION - 3-WAY ENGINE COMPARISON")
        logger.info("=" * 80)

        runner = get_comparison_runner()

        # Run 3-way comparison: Unified vs Deterministic vs Quick
        logger.info("\nRunning 3-way comparison: unified vs deterministic vs quick")
        logger.info("Ticker: MES, Days: 30")
        logger.info("\nExpected divergence:")
        logger.info("- Unified: Regime-aware ensemble scoring")
        logger.info("- Deterministic: Multi-TF strict alignment (>=4/5 TFs, 75% conf, 2:1 R:R, 4hr max)")
        logger.info("- Quick: Fast 5m momentum (60% conf, 1.5:1 R:R, 2hr max, volume required)")

        comparison = await runner.run_engine_comparison(
            ticker='MES',
            days=30,
            engines=['unified', 'deterministic', 'quick'],
            config_overrides={'initial_capital': 25000}
        )

        logger.info("\n" + "=" * 80)
        logger.info("EXECUTION METADATA (Phase 2C Honesty Tracking)")
        logger.info("=" * 80)

        fallback_count = 0
        for engine, metadata in comparison.engine_metadata.items():
            logger.info(f"\n{engine.upper()}:")
            logger.info(f"  Requested: {metadata.requested_engine_type}")
            logger.info(f"  Actual Mode: {metadata.actual_execution_mode}")
            logger.info(f"  Fallback Used: {metadata.unified_fallback_used}")
            logger.info(f"  Routing Status: {metadata.routing_status}")
            logger.info(f"  Notes: {metadata.notes}")

            if metadata.unified_fallback_used:
                fallback_count += 1

        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE LEADERBOARD")
        logger.info("=" * 80)

        for entry in comparison.leaderboard:
            logger.info(
                f"\n#{entry['rank']} {entry['engine'].upper():<15} "
                f"Return={entry['total_return_pct']:>6.2f}% | "
                f"Sharpe={entry['sharpe_ratio']:>5.2f} | "
                f"Win={entry['win_rate']:>5.1f}% | "
                f"Trades={entry['total_trades']:>3} | "
                f"Avg Hold={entry['avg_holding_time_hours']:>5.1f}h"
            )

        logger.info("\n" + "=" * 80)
        logger.info("DIVERGENCE ANALYSIS")
        logger.info("=" * 80)

        # Extract metrics for comparison
        engines = ['unified', 'deterministic', 'quick']
        metrics = {}
        for engine in engines:
            for entry in comparison.leaderboard:
                if entry['engine'] == engine:
                    metrics[engine] = entry
                    break

        if len(metrics) == 3:
            # Compare trade counts
            unified_trades = metrics['unified']['total_trades']
            det_trades = metrics['deterministic']['total_trades']
            quick_trades = metrics['quick']['total_trades']

            logger.info(f"\nTrade Count Divergence:")
            logger.info(f"  Unified: {unified_trades} trades")
            logger.info(f"  Deterministic: {det_trades} trades ({det_trades - unified_trades:+d} vs Unified)")
            logger.info(f"  Quick: {quick_trades} trades ({quick_trades - unified_trades:+d} vs Unified)")

            # Compare holding times
            unified_hold = metrics['unified']['avg_holding_time_hours']
            det_hold = metrics['deterministic']['avg_holding_time_hours']
            quick_hold = metrics['quick']['avg_holding_time_hours']

            logger.info(f"\nHolding Time Divergence:")
            logger.info(f"  Unified: {unified_hold:.1f}h average")
            logger.info(f"  Deterministic: {det_hold:.1f}h average ({det_hold - unified_hold:+.1f}h vs Unified)")
            logger.info(f"  Quick: {quick_hold:.1f}h average ({quick_hold - unified_hold:+.1f}h vs Unified)")

            # Expected pattern check
            logger.info(f"\nExpected Pattern Check:")
            quick_faster = quick_hold < det_hold
            quick_more_trades = quick_trades > det_trades

            logger.info(f"  ✓ Quick faster than Deterministic? {quick_faster} (Quick={quick_hold:.1f}h, Det={det_hold:.1f}h)")
            logger.info(f"  ✓ Quick more trades than Deterministic? {quick_more_trades} (Quick={quick_trades}, Det={det_trades})")

        # Show warnings
        logger.info("\n" + "=" * 80)
        logger.info("WARNINGS")
        logger.info("=" * 80)

        if comparison.warnings:
            for warning in comparison.warnings:
                logger.warning(f"  - {warning}")
        else:
            logger.info("  ✅ NO FALLBACK WARNINGS - ALL ENGINES FULLY ROUTED")

        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2C VERIFICATION SUMMARY")
        logger.info("=" * 80)

        logger.info(f"\n✓ Engines tested: {len(comparison.engines_compared)}")
        logger.info(f"✓ Engines fully routed: {len(comparison.engine_metadata) - fallback_count}/{len(comparison.engine_metadata)}")
        logger.info(f"✓ Real divergence observed: {len(set(e['total_trades'] for e in comparison.leaderboard)) > 1}")

        success = (
            fallback_count == 0 and  # No fallbacks
            len(comparison.leaderboard) == 3 and  # All 3 engines ran
            len(set(e['total_trades'] for e in comparison.leaderboard)) > 1  # Results diverge
        )

        if success:
            logger.info("\n🎉 PHASE 2C COMPLETE - ALL ENGINES FULLY ROUTED WITH REAL DIVERGENCE")
            logger.info("\nREADY FOR PHASE 3: ADAPTIVE ROUTER")
        else:
            logger.warning("\n⚠️  PHASE 2C INCOMPLETE - Some engines still using fallback or no divergence")

        logger.info("\n" + "=" * 80)

        return comparison

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    result = asyncio.run(test_phase2c_complete())
    sys.exit(0 if result else 1)
