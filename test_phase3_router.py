"""
Phase 3 Router Verification
============================

Tests:
1. Router status and modes
2. Regime-based routing decisions
3. Manual override functionality
4. Regime-to-engine mapping
"""
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_router():
    """Test the adaptive router."""
    try:
        from app.services.smartflow_engine_router import (
            get_router, RoutingMode, DecisionSource,
            AUTO_ELIGIBLE_ENGINES, MANUAL_ONLY_ENGINES
        )

        logger.info("=" * 80)
        logger.info("PHASE 3: ADAPTIVE ROUTER VERIFICATION")
        logger.info("=" * 80)

        router = get_router()

        # Test 1: Initial Status
        logger.info("\n--- TEST 1: Initial Router Status ---")
        status = router.get_router_status()
        logger.info(f"Routing Mode: {status['routing_mode']}")
        logger.info(f"Manual Override: {status['manual_override_engine']}")
        logger.info(f"Auto-Eligible Engines: {status['auto_eligible_engines']}")
        logger.info(f"Manual-Only Engines: {status['manual_only_engines']}")

        assert status['routing_mode'] == 'manual', "Default mode should be manual"
        assert status['auto_eligible_engines'] == ['unified', 'deterministic', 'quick']
        assert status['manual_only_engines'] == ['ai', 'flow']

        logger.info("✓ Status check passed")

        # Test 2: Manual Mode Decisions
        logger.info("\n--- TEST 2: Manual Mode Decisions ---")
        decision = router.route_signal_request('trending_up', 0.8)
        logger.info(f"Regime: trending_up → Engine: {decision.selected_engine}")
        logger.info(f"Decision Source: {decision.decision_source.value}")
        logger.info(f"Reason: {decision.decision_reason}")

        assert decision.routing_mode == RoutingMode.MANUAL
        logger.info("✓ Manual mode decision passed")

        # Test 3: Auto Mode Regime Routing
        logger.info("\n--- TEST 3: Auto-By-Regime Routing ---")
        router.set_routing_mode(RoutingMode.AUTO_BY_REGIME)

        test_regimes = [
            ('ranging', 'deterministic', 'Ranging should prefer deterministic'),
            ('mean_reverting', 'deterministic', 'Mean-reverting should prefer deterministic'),
            ('trending_up', 'quick', 'Trending up should prefer quick'),
            ('trending_down', 'quick', 'Trending down should prefer quick'),
            ('vol_expansion', 'quick', 'Vol expansion should prefer quick'),
            ('neutral', 'unified', 'Neutral should prefer unified'),
        ]

        for regime, expected_engine, description in test_regimes:
            decision = router.route_signal_request(regime, 0.7)
            logger.info(f"  {regime:20} → {decision.selected_engine:15} (expected: {expected_engine})")

            assert decision.selected_engine == expected_engine, f"{description}"
            assert decision.decision_source == DecisionSource.FALLBACK_RULE
            assert decision.eligible_engines == AUTO_ELIGIBLE_ENGINES

        logger.info("✓ Auto-by-regime routing passed")

        # Test 4: Regime Mapping
        logger.info("\n--- TEST 4: Regime-to-Engine Mapping ---")
        mapping = router.get_regime_mapping()

        for regime, info in sorted(mapping.items()):
            source_label = "📊 DATA" if info['is_data_backed'] else "📋 RULE"
            logger.info(
                f"  {regime:20} → {info['preferred_engine']:15} "
                f"{source_label} (conf: {info['confidence']:.1f})"
            )

        # Verify key mappings
        assert mapping['ranging']['preferred_engine'] == 'deterministic'
        assert mapping['trending_up']['preferred_engine'] == 'quick'
        assert mapping['neutral']['preferred_engine'] == 'unified'

        # All should be rule-based (no comparison data yet)
        for regime, info in mapping.items():
            assert not info['is_data_backed'], f"{regime} should use fallback rule"

        logger.info("✓ Regime mapping passed")

        # Test 5: Manual Override
        logger.info("\n--- TEST 5: Manual Override ---")

        # Set override to 'deterministic'
        router.set_manual_override('deterministic')

        decision = router.route_signal_request('trending_up', 0.8)
        logger.info(f"Override to deterministic → Engine: {decision.selected_engine}")
        assert decision.selected_engine == 'deterministic'
        assert decision.decision_source == DecisionSource.MANUAL_OVERRIDE
        assert decision.manual_override == 'deterministic'

        # Clear override
        router.set_manual_override(None)
        decision = router.route_signal_request('trending_up', 0.8)
        logger.info(f"Override cleared → Engine: {decision.selected_engine}")
        assert decision.selected_engine == 'quick'  # Should return to auto logic

        logger.info("✓ Manual override passed")

        # Test 6: Decision Explanation
        logger.info("\n--- TEST 6: Decision Explanations ---")

        router.set_manual_override(None)

        decisions = [
            router.route_signal_request('ranging', 0.8),
            router.route_signal_request('trending_up', 0.7),
            router.route_signal_request('neutral', 0.5),
        ]

        for decision in decisions:
            explanation = router.explain_engine_selection(decision)
            logger.info(f"  {decision.current_regime:20} → {explanation}")

        logger.info("✓ Decision explanations passed")

        # Test 7: Engine Eligibility
        logger.info("\n--- TEST 7: Engine Eligibility ---")
        logger.info(f"Auto-Eligible: {AUTO_ELIGIBLE_ENGINES}")
        logger.info(f"Manual-Only: {MANUAL_ONLY_ENGINES}")

        # Verify AI and Flow are NOT in auto-eligible
        assert 'ai' not in AUTO_ELIGIBLE_ENGINES
        assert 'flow' not in AUTO_ELIGIBLE_ENGINES

        # But they can be set as manual override
        router.set_manual_override('ai')
        decision = router.route_signal_request('trending_up', 0.8)
        assert decision.selected_engine == 'ai'
        logger.info("✓ AI can be manually selected (but not auto-preferred)")

        router.set_manual_override('flow')
        decision = router.route_signal_request('ranging', 0.8)
        assert decision.selected_engine == 'flow'
        logger.info("✓ Flow can be manually selected (but not auto-preferred)")

        router.set_manual_override(None)

        logger.info("✓ Engine eligibility passed")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3 ROUTER VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info("✓ All tests passed!")
        logger.info("\nRouter Features Verified:")
        logger.info("  ✓ Manual and Auto-by-Regime modes")
        logger.info("  ✓ Regime-based routing decisions")
        logger.info("  ✓ Transparent fallback rules")
        logger.info("  ✓ Manual override functionality")
        logger.info("  ✓ Regime-to-engine mapping")
        logger.info("  ✓ Decision explanations")
        logger.info("  ✓ Engine eligibility (auto vs manual-only)")
        logger.info("\nAuto-Eligible Engines: unified, deterministic, quick")
        logger.info("Manual-Only Engines: ai, flow")
        logger.info("\n" + "=" * 80)

        return True

    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import sys
    success = test_router()
    sys.exit(0 if success else 1)
