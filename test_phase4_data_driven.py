"""
Phase 4 Data-Driven Router Verification
=========================================

Tests:
1. Run backtest comparison (unified vs deterministic vs quick)
2. Verify comparison results are saved to store
3. Verify router loads comparison data automatically
4. Verify decision_source becomes 'comparison_results' for regimes with data
5. Verify fallback_rule is still used for regimes without data
6. Verify UI can distinguish data-backed vs rule-backed decisions
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


async def test_phase4_data_driven():
    """Test data-driven router with real comparison data."""
    try:
        from app.services.backtesting.comparison_runner import get_comparison_runner
        from app.services.backtesting.comparison_store import get_comparison_store
        from app.services.smartflow_engine_router import get_router, DecisionSource

        logger.info("=" * 80)
        logger.info("PHASE 4: DATA-DRIVEN ROUTER VERIFICATION")
        logger.info("=" * 80)

        # Clear existing data for clean test
        logger.info("\n--- Clearing existing comparison data ---")
        store = get_comparison_store()
        store.clear_all_data()
        logger.info("✓ Comparison store cleared")

        # Test 1: Run comparison to generate regime data
        logger.info("\n--- TEST 1: Running Engine Comparison ---")
        logger.info("Engines: unified, deterministic, quick")
        logger.info("Ticker: MES, Days: 30")
        logger.info("(This will generate regime-specific performance data)")

        runner = get_comparison_runner()
        comparison = await runner.run_engine_comparison(
            ticker='MES',
            days=30,
            engines=['unified', 'deterministic', 'quick'],
            config_overrides={'initial_capital': 25000}
        )

        logger.info(f"\n✓ Comparison complete: {comparison.comparison_id}")
        logger.info(f"  Engines compared: {comparison.engines_compared}")
        logger.info(f"  Regimes with data: {list(comparison.regime_comparison.keys())}")

        # Test 2: Verify comparison was saved to store
        logger.info("\n--- TEST 2: Verifying Comparison Store ---")

        regime_rankings = store.get_all_regime_rankings()
        logger.info(f"Regimes in store: {list(regime_rankings.keys())}")

        assert len(regime_rankings) > 0, "Store should have regime data"
        logger.info(f"✓ Store has data for {len(regime_rankings)} regimes")

        # Show one regime's data
        if regime_rankings:
            sample_regime = list(regime_rankings.keys())[0]
            sample_data = regime_rankings[sample_regime]

            logger.info(f"\nSample regime '{sample_regime}':")
            logger.info(f"  Ranked engines: {sample_data['ranked_engines']}")
            logger.info(f"  Sample count: {sample_data['sample_count']}")
            logger.info(f"  Last updated: {sample_data['last_updated']}")

            if sample_data['engine_metrics']:
                logger.info(f"  Engine metrics:")
                for engine, metrics in sample_data['engine_metrics'].items():
                    logger.info(
                        f"    {engine:15} - WR: {metrics.get('win_rate', 0)*100:5.1f}%, "
                        f"P&L: ${metrics.get('pnl', 0):7.2f}"
                    )

        # Test 3: Create fresh router instance and verify it loads comparison data
        logger.info("\n--- TEST 3: Router Loading Comparison Data ---")

        # Reset router instance to force reload
        from app.services import smartflow_engine_router
        smartflow_engine_router._router_instance = None

        router = get_router()  # This should load from store in __init__

        # Check router status
        status = router.get_router_status()

        logger.info(f"Comparison rankings loaded: {status['comparison_rankings_available']}")
        logger.info(f"Fallback rules available: {status['fallback_rules_available']}")

        assert len(status['comparison_rankings_available']) > 0, \
            "Router should have loaded comparison rankings"

        logger.info(f"✓ Router loaded comparison data for {len(status['comparison_rankings_available'])} regimes")

        # Test 4: Verify decision_source changes to comparison_results
        logger.info("\n--- TEST 4: Verifying Data-Backed Decisions ---")

        from app.services.smartflow_engine_router import RoutingMode
        router.set_routing_mode(RoutingMode.AUTO_BY_REGIME)

        # Test a regime that should have comparison data
        data_backed_regimes = status['comparison_rankings_available']

        if data_backed_regimes:
            test_regime = data_backed_regimes[0]
            logger.info(f"\nTesting regime with comparison data: '{test_regime}'")

            decision = router.route_signal_request(test_regime, 0.8)

            logger.info(f"  Selected engine: {decision.selected_engine}")
            logger.info(f"  Decision source: {decision.decision_source.value}")
            logger.info(f"  Fallback used: {decision.fallback_used}")
            logger.info(f"  Reason: {decision.decision_reason}")

            # CRITICAL: Decision should be comparison_results, not fallback_rule
            assert decision.decision_source == DecisionSource.COMPARISON_RESULTS, \
                f"Expected comparison_results, got {decision.decision_source.value}"

            assert not decision.fallback_used, \
                "Fallback should not be used when comparison data exists"

            logger.info(f"  ✓ Decision source correctly set to: comparison_results")
        else:
            logger.warning("  ⚠️  No comparison data loaded - cannot verify data-backed decisions")

        # Test 5: Verify fallback still works for regimes without data
        logger.info("\n--- TEST 5: Verifying Fallback for Missing Data ---")

        # Find a regime that doesn't have comparison data
        all_possible_regimes = set(status['fallback_rules_available'])
        regimes_with_data = set(status['comparison_rankings_available'])
        regimes_without_data = all_possible_regimes - regimes_with_data

        if regimes_without_data:
            test_regime = list(regimes_without_data)[0]
            logger.info(f"\nTesting regime without comparison data: '{test_regime}'")

            decision = router.route_signal_request(test_regime, 0.7)

            logger.info(f"  Selected engine: {decision.selected_engine}")
            logger.info(f"  Decision source: {decision.decision_source.value}")
            logger.info(f"  Fallback used: {decision.fallback_used}")
            logger.info(f"  Reason: {decision.decision_reason}")

            # Should use fallback rule
            assert decision.decision_source == DecisionSource.FALLBACK_RULE, \
                f"Expected fallback_rule for regime without data, got {decision.decision_source.value}"

            assert decision.fallback_used, \
                "Fallback should be used when no comparison data exists"

            logger.info(f"  ✓ Correctly using fallback_rule for regime without data")
        else:
            logger.info("  (All regimes have comparison data - skipping fallback test)")

        # Test 6: Verify regime mapping shows data-backed vs rule-backed
        logger.info("\n--- TEST 6: Regime Mapping Transparency ---")

        mapping = router.get_regime_mapping()

        logger.info("\nRegime Mapping (showing data source):")
        data_backed_count = 0
        rule_backed_count = 0

        for regime in sorted(mapping.keys()):
            info = mapping[regime]
            source_label = "📊 DATA" if info['is_data_backed'] else "📋 RULE"
            logger.info(
                f"  {regime:20} → {info['preferred_engine']:15} "
                f"{source_label:10} (conf: {info['confidence']:.2f})"
            )

            if info['is_data_backed']:
                data_backed_count += 1
            else:
                rule_backed_count += 1

        logger.info(f"\nSummary:")
        logger.info(f"  Data-backed regimes: {data_backed_count}")
        logger.info(f"  Rule-backed regimes: {rule_backed_count}")

        assert data_backed_count > 0, "Should have at least one data-backed regime"
        logger.info(f"✓ Regime mapping correctly distinguishes data vs rules")

        # Test 7: Verify comparison history
        logger.info("\n--- TEST 7: Comparison History ---")

        history = store.get_comparison_history(limit=5)
        logger.info(f"Recent comparisons: {len(history)}")

        for item in history:
            logger.info(
                f"  {item['comparison_id']}: {item['ticker']} "
                f"({len(item['engines'])} engines, {len(item.get('regimes', []))} regimes)"
            )

        logger.info(f"✓ Comparison history working")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4 DATA-DRIVEN ROUTER VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info("✓ All tests passed!")
        logger.info("\nPhase 4 Features Verified:")
        logger.info("  ✓ Comparison results persisted to store")
        logger.info("  ✓ Router automatically loads comparison data on init")
        logger.info("  ✓ decision_source = 'comparison_results' for regimes with data")
        logger.info("  ✓ decision_source = 'fallback_rule' for regimes without data")
        logger.info("  ✓ Regime mapping shows data-backed vs rule-backed")
        logger.info("  ✓ Comparison history tracked")
        logger.info("\nRouter Upgrade:")
        logger.info(f"  Phase 3: All decisions used fallback rules")
        logger.info(f"  Phase 4: {data_backed_count} regime(s) now use comparison data")
        logger.info("\nData-Driven Evidence:")
        for regime in status['comparison_rankings_available'][:3]:  # Show first 3
            ranking = mapping[regime]
            logger.info(f"  {regime} → {ranking['preferred_engine']} (from backtest data)")
        logger.info("\n" + "=" * 80)

        return comparison

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    result = asyncio.run(test_phase4_data_driven())
    sys.exit(0 if result else 1)
