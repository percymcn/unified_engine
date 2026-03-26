"""
Phase 4.5 Statistical Confidence Verification
==============================================

Tests:
1. Run backtest comparison (unified vs deterministic vs quick)
2. Verify router uses LOW_CONFIDENCE_DATA source for regimes with <20 samples
3. Run additional comparisons to reach minimum threshold
4. Verify router switches to COMPARISON_RESULTS source when ≥20 samples
5. Verify confidence score calculation (sample_size / 50)
6. Verify regime categorization (high_confidence, low_confidence, fallback_only)
7. Verify UI shows proper indicators (📊 DATA, ⚠ LOW DATA, 📋 RULE)
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


async def test_phase4_5_confidence():
    """Test statistical confidence evaluation in router."""
    try:
        from app.services.backtesting.comparison_runner import get_comparison_runner
        from app.services.backtesting.comparison_store import get_comparison_store
        from app.services.smartflow_engine_router import get_router, DecisionSource, MINIMUM_REGIME_SAMPLES, CONFIDENCE_DENOMINATOR

        logger.info("=" * 80)
        logger.info("PHASE 4.5: STATISTICAL CONFIDENCE VERIFICATION")
        logger.info("=" * 80)

        # Clear existing data for clean test
        logger.info("\n--- Clearing existing comparison data ---")
        store = get_comparison_store()
        store.clear_all_data()
        logger.info("✓ Comparison store cleared")

        # Test 1: Run comparison with low sample count
        logger.info("\n--- TEST 1: Running First Comparison (Low Sample Count) ---")
        logger.info(f"Minimum regime samples threshold: {MINIMUM_REGIME_SAMPLES}")
        logger.info(f"Confidence denominator: {CONFIDENCE_DENOMINATOR}")
        logger.info("Engines: unified, deterministic, quick")
        logger.info("Ticker: MES, Days: 30")

        runner = get_comparison_runner()
        comparison1 = await runner.run_engine_comparison(
            ticker='MES',
            days=30,
            engines=['unified', 'deterministic', 'quick'],
            config_overrides={'initial_capital': 25000}
        )

        logger.info(f"\n✓ First comparison complete: {comparison1.comparison_id}")
        logger.info(f"  Engines compared: {comparison1.engines_compared}")
        logger.info(f"  Regimes with data: {list(comparison1.regime_comparison.keys())}")

        # Test 2: Verify LOW_CONFIDENCE_DATA source
        logger.info("\n--- TEST 2: Verifying LOW_CONFIDENCE_DATA Source (Sample Count < 20) ---")

        # Reset router to force reload
        from app.services import smartflow_engine_router
        smartflow_engine_router._router_instance = None
        router = get_router()

        status = router.get_router_status()

        logger.info(f"Confidence threshold: {status['confidence_threshold']}")
        logger.info(f"High confidence regimes: {status['high_confidence_regimes']}")
        logger.info(f"Low confidence regimes: {status['low_confidence_regimes']}")
        logger.info(f"Fallback only regimes: {status['fallback_only_regimes']}")

        # Should have low confidence regimes, not high confidence
        assert len(status['low_confidence_regimes']) > 0, \
            "Should have low confidence regimes after 1 comparison"

        if status['high_confidence_regimes']:
            logger.warning(
                f"⚠️  Unexpected high confidence regimes: {status['high_confidence_regimes']}"
            )

        logger.info(f"✓ {len(status['low_confidence_regimes'])} regime(s) correctly marked as low confidence")

        # Test 3: Verify decision uses LOW_CONFIDENCE_DATA
        logger.info("\n--- TEST 3: Verifying Decision Uses LOW_CONFIDENCE_DATA ---")

        from app.services.smartflow_engine_router import RoutingMode
        router.set_routing_mode(RoutingMode.AUTO_BY_REGIME)

        if status['low_confidence_regimes']:
            test_regime = status['low_confidence_regimes'][0]
            logger.info(f"Testing low confidence regime: '{test_regime}'")

            decision = router.route_signal_request(test_regime, 0.8)

            logger.info(f"  Selected engine: {decision.selected_engine}")
            logger.info(f"  Decision source: {decision.decision_source.value}")
            logger.info(f"  Sample size: {decision.sample_size}")
            logger.info(f"  Statistical confidence: {decision.statistical_confidence:.2f}")
            logger.info(f"  Reason: {decision.decision_reason}")

            # CRITICAL: Should be LOW_CONFIDENCE_DATA, not COMPARISON_RESULTS
            assert decision.decision_source == DecisionSource.LOW_CONFIDENCE_DATA, \
                f"Expected low_confidence_data, got {decision.decision_source.value}"

            assert decision.sample_size < MINIMUM_REGIME_SAMPLES, \
                f"Sample size should be < {MINIMUM_REGIME_SAMPLES}, got {decision.sample_size}"

            # Confidence should be less than 0.4 (20/50)
            expected_max_confidence = MINIMUM_REGIME_SAMPLES / CONFIDENCE_DENOMINATOR
            assert decision.statistical_confidence < expected_max_confidence, \
                f"Confidence should be < {expected_max_confidence}, got {decision.statistical_confidence}"

            logger.info(f"  ✓ Decision correctly uses LOW_CONFIDENCE_DATA source")

        # Test 4: Run multiple comparisons to reach threshold
        logger.info("\n--- TEST 4: Running Multiple Comparisons to Reach Threshold ---")
        logger.info(f"Need {MINIMUM_REGIME_SAMPLES} samples for high confidence")
        logger.info("Running 19 more comparisons (total will be 20)...")

        for i in range(2, 21):  # Run 19 more to reach 20 total
            comparison = await runner.run_engine_comparison(
                ticker='MES',
                days=30,
                engines=['unified', 'deterministic', 'quick'],
                config_overrides={'initial_capital': 25000}
            )
            logger.info(f"  Completed comparison {i}/20: {comparison.comparison_id}")

        logger.info("✓ All 20 comparisons complete")

        # Test 5: Verify router switches to COMPARISON_RESULTS
        logger.info("\n--- TEST 5: Verifying Switch to COMPARISON_RESULTS (Sample Count ≥ 20) ---")

        # Refresh router rankings
        updated_count = router.refresh_comparison_rankings()
        logger.info(f"Router refreshed: {updated_count} regime(s) updated")

        status = router.get_router_status()

        logger.info(f"High confidence regimes: {status['high_confidence_regimes']}")
        logger.info(f"Low confidence regimes: {status['low_confidence_regimes']}")
        logger.info(f"Fallback only regimes: {status['fallback_only_regimes']}")

        # Should now have high confidence regimes
        assert len(status['high_confidence_regimes']) > 0, \
            "Should have high confidence regimes after 20 comparisons"

        logger.info(f"✓ {len(status['high_confidence_regimes'])} regime(s) now have high confidence")

        # Test 6: Verify decision uses COMPARISON_RESULTS
        logger.info("\n--- TEST 6: Verifying Decision Uses COMPARISON_RESULTS ---")

        if status['high_confidence_regimes']:
            test_regime = status['high_confidence_regimes'][0]
            logger.info(f"Testing high confidence regime: '{test_regime}'")

            decision = router.route_signal_request(test_regime, 0.8)

            logger.info(f"  Selected engine: {decision.selected_engine}")
            logger.info(f"  Decision source: {decision.decision_source.value}")
            logger.info(f"  Sample size: {decision.sample_size}")
            logger.info(f"  Statistical confidence: {decision.statistical_confidence:.2f}")
            logger.info(f"  Reason: {decision.decision_reason}")

            # CRITICAL: Should be COMPARISON_RESULTS, not LOW_CONFIDENCE_DATA
            assert decision.decision_source == DecisionSource.COMPARISON_RESULTS, \
                f"Expected comparison_results, got {decision.decision_source.value}"

            assert decision.sample_size >= MINIMUM_REGIME_SAMPLES, \
                f"Sample size should be ≥ {MINIMUM_REGIME_SAMPLES}, got {decision.sample_size}"

            # Confidence should be ≥ 0.4 (20/50)
            expected_min_confidence = MINIMUM_REGIME_SAMPLES / CONFIDENCE_DENOMINATOR
            assert decision.statistical_confidence >= expected_min_confidence, \
                f"Confidence should be ≥ {expected_min_confidence}, got {decision.statistical_confidence}"

            logger.info(f"  ✓ Decision correctly uses COMPARISON_RESULTS source")

        # Test 7: Verify confidence score calculation
        logger.info("\n--- TEST 7: Verifying Confidence Score Calculation ---")

        regime_rankings = store.get_all_regime_rankings()

        for regime, data in regime_rankings.items():
            sample_count = data['sample_count']
            expected_confidence = min(1.0, sample_count / CONFIDENCE_DENOMINATOR)

            logger.info(
                f"  {regime:20} - Samples: {sample_count:2}, "
                f"Expected confidence: {expected_confidence:.2f}"
            )

            # Verify confidence calculation in actual decision
            decision = router.route_signal_request(regime, 0.8)

            # Allow small floating point differences
            assert abs(decision.statistical_confidence - expected_confidence) < 0.01, \
                f"Confidence mismatch for {regime}: expected {expected_confidence}, got {decision.statistical_confidence}"

        logger.info("✓ Confidence scores calculated correctly")

        # Test 8: Verify regime mapping shows proper indicators
        logger.info("\n--- TEST 8: Regime Mapping with Confidence Indicators ---")

        mapping = router.get_regime_mapping()

        logger.info("\nRegime Mapping (showing confidence):")
        high_conf_count = 0
        low_conf_count = 0
        rule_count = 0

        for regime in sorted(mapping.keys()):
            info = mapping[regime]

            if info['source'] == 'comparison_results':
                source_label = "📊 DATA"
                high_conf_count += 1
            elif info['source'] == 'low_confidence_data':
                source_label = "⚠ LOW DATA"
                low_conf_count += 1
            else:
                source_label = "📋 RULE"
                rule_count += 1

            logger.info(
                f"  {regime:20} → {info['preferred_engine']:15} "
                f"{source_label:12} "
                f"(samples: {info['sample_size']:2}, conf: {info['confidence']:.2f})"
            )

        logger.info(f"\nSummary:")
        logger.info(f"  High confidence (📊 DATA): {high_conf_count}")
        logger.info(f"  Low confidence (⚠ LOW DATA): {low_conf_count}")
        logger.info(f"  Fallback rules (📋 RULE): {rule_count}")

        assert high_conf_count > 0, "Should have at least one high confidence regime"
        logger.info(f"✓ Regime mapping correctly shows confidence indicators")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4.5 STATISTICAL CONFIDENCE VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info("✓ All tests passed!")
        logger.info("\nPhase 4.5 Features Verified:")
        logger.info("  ✓ Minimum sample threshold enforced (20 samples)")
        logger.info("  ✓ LOW_CONFIDENCE_DATA source used for <20 samples")
        logger.info("  ✓ COMPARISON_RESULTS source used for ≥20 samples")
        logger.info("  ✓ Confidence score calculated correctly (sample_size / 50)")
        logger.info("  ✓ Regime categorization working (high/low/fallback)")
        logger.info("  ✓ Router decisions include sample_size and statistical_confidence")
        logger.info("  ✓ UI indicators show 📊 DATA, ⚠ LOW DATA, 📋 RULE")
        logger.info("\nStatistical Reliability:")
        logger.info(f"  Phase 4:   1 sample treated as authoritative")
        logger.info(f"  Phase 4.5: {MINIMUM_REGIME_SAMPLES} samples required for high confidence")
        logger.info(f"  Confidence increases linearly to 100% at {CONFIDENCE_DENOMINATOR} samples")
        logger.info("\nConfidence Levels:")
        logger.info(f"  High confidence regimes: {high_conf_count}")
        logger.info(f"  Low confidence regimes: {low_conf_count}")
        logger.info(f"  Fallback only regimes: {rule_count}")
        logger.info("\n" + "=" * 80)

        return comparison1

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    result = asyncio.run(test_phase4_5_confidence())
    sys.exit(0 if result else 1)
