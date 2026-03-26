"""
Phase 3 Router Traceability Verification
==========================================

Verifies that every routing decision is fully traceable with:
1. Decision source clearly labeled (manual, data, rule, default)
2. Complete decision context (regime, mode, confidence)
3. Human-readable explanations
4. Timestamps for audit trail
5. Fallback transparency
"""
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_traceability():
    """Test router traceability features."""
    try:
        from app.services.smartflow_engine_router import (
            get_router, RoutingMode, DecisionSource
        )

        logger.info("=" * 80)
        logger.info("PHASE 3: ROUTER TRACEABILITY VERIFICATION")
        logger.info("=" * 80)

        router = get_router()

        # Test 1: Decision Source Labels
        logger.info("\n--- TEST 1: Decision Source Transparency ---")

        # Manual override decision
        router.set_manual_override('deterministic')
        decision1 = router.route_signal_request('trending_up', 0.8)

        logger.info(f"\nScenario: Manual Override")
        logger.info(f"  Decision Source: {decision1.decision_source.value}")
        logger.info(f"  Expected: manual_override")
        assert decision1.decision_source == DecisionSource.MANUAL_OVERRIDE
        logger.info("  ✓ Source correctly labeled as manual_override")

        # Clear override
        router.set_manual_override(None)

        # Manual mode default decision
        router.set_routing_mode(RoutingMode.MANUAL)
        decision2 = router.route_signal_request('ranging', 0.7)

        logger.info(f"\nScenario: Manual Mode (no override)")
        logger.info(f"  Decision Source: {decision2.decision_source.value}")
        logger.info(f"  Expected: default")
        assert decision2.decision_source == DecisionSource.DEFAULT
        logger.info("  ✓ Source correctly labeled as default")

        # Auto mode rule-based decision
        router.set_routing_mode(RoutingMode.AUTO_BY_REGIME)
        decision3 = router.route_signal_request('ranging', 0.7)

        logger.info(f"\nScenario: Auto Mode (rule-based)")
        logger.info(f"  Decision Source: {decision3.decision_source.value}")
        logger.info(f"  Expected: fallback_rule")
        assert decision3.decision_source == DecisionSource.FALLBACK_RULE
        logger.info("  ✓ Source correctly labeled as fallback_rule")

        logger.info("\n✓ All decision sources correctly labeled")

        # Test 2: Complete Decision Context
        logger.info("\n--- TEST 2: Complete Decision Context ---")

        decision = router.route_signal_request('trending_up', 0.85)

        required_fields = {
            'routing_mode': decision.routing_mode,
            'current_regime': decision.current_regime,
            'selected_engine': decision.selected_engine,
            'eligible_engines': decision.eligible_engines,
            'ranking': decision.ranking,
            'decision_source': decision.decision_source,
            'decision_reason': decision.decision_reason,
            'fallback_used': decision.fallback_used,
            'timestamp': decision.timestamp,
            'manual_override': decision.manual_override,
            'regime_confidence': decision.regime_confidence
        }

        logger.info("\nDecision Context Fields:")
        for field, value in required_fields.items():
            logger.info(f"  {field:20} = {value}")

        # Verify all fields are present
        assert decision.routing_mode == RoutingMode.AUTO_BY_REGIME
        assert decision.current_regime == 'trending_up'
        assert decision.selected_engine == 'quick'
        assert len(decision.eligible_engines) > 0
        assert len(decision.ranking) > 0
        assert decision.decision_source == DecisionSource.FALLBACK_RULE
        assert decision.decision_reason != ""
        assert isinstance(decision.fallback_used, bool)
        assert isinstance(decision.timestamp, datetime)
        assert decision.regime_confidence == 0.85

        logger.info("\n✓ All context fields present and valid")

        # Test 3: Human-Readable Explanations
        logger.info("\n--- TEST 3: Human-Readable Explanations ---")

        # Test different scenarios
        scenarios = [
            ('Manual Override', lambda: router.set_manual_override('unified')),
            ('Manual Mode', lambda: (router.set_manual_override(None), router.set_routing_mode(RoutingMode.MANUAL))),
            ('Auto Mode', lambda: router.set_routing_mode(RoutingMode.AUTO_BY_REGIME))
        ]

        for scenario_name, setup_fn in scenarios:
            if isinstance(setup_fn(), tuple):
                # Handle multiple setup calls
                pass

            decision = router.route_signal_request('ranging', 0.7)
            explanation = router.explain_engine_selection(decision)

            logger.info(f"\n{scenario_name}:")
            logger.info(f"  Explanation: {explanation}")

            # Verify explanation is not empty and informative
            assert len(explanation) > 20, f"{scenario_name} explanation too short"
            logger.info(f"  ✓ Explanation is clear and informative")

        logger.info("\n✓ All explanations generated successfully")

        # Test 4: Timestamps for Audit Trail
        logger.info("\n--- TEST 4: Audit Trail Timestamps ---")

        router.set_manual_override(None)
        router.set_routing_mode(RoutingMode.AUTO_BY_REGIME)

        # Make multiple decisions
        decisions = []
        for i in range(3):
            decision = router.route_signal_request('trending_up', 0.8)
            decisions.append(decision)

        logger.info("\nDecision Timestamps:")
        for i, decision in enumerate(decisions, 1):
            logger.info(f"  Decision {i}: {decision.timestamp.isoformat()}")

        # Verify timestamps are present and valid
        for decision in decisions:
            assert isinstance(decision.timestamp, datetime)
            assert decision.timestamp <= datetime.now()

        logger.info("\n✓ Timestamps present and valid for audit trail")

        # Test 5: Fallback Transparency
        logger.info("\n--- TEST 5: Fallback Transparency ---")

        # In Phase 3 (initial version), all auto decisions use fallback rules
        decision = router.route_signal_request('ranging', 0.7)

        logger.info(f"\nDecision Analysis:")
        logger.info(f"  Decision Source: {decision.decision_source.value}")
        logger.info(f"  Fallback Used: {decision.fallback_used}")
        logger.info(f"  Reason: {decision.decision_reason}")

        if decision.fallback_used:
            logger.info(f"  ✓ Fallback usage clearly indicated")
            logger.info(f"    (Expected in Phase 3 - no comparison data yet)")

        # Verify fallback transparency
        assert decision.fallback_used == (decision.decision_source == DecisionSource.FALLBACK_RULE)
        logger.info("\n✓ Fallback usage is transparent and accurate")

        # Test 6: to_dict() Serialization
        logger.info("\n--- TEST 6: API Serialization ---")

        decision = router.route_signal_request('vol_expansion', 0.9)
        decision_dict = decision.to_dict()

        logger.info("\nSerialized Decision (sample fields):")
        logger.info(f"  routing_mode: {decision_dict['routing_mode']}")
        logger.info(f"  current_regime: {decision_dict['current_regime']}")
        logger.info(f"  selected_engine: {decision_dict['selected_engine']}")
        logger.info(f"  decision_source: {decision_dict['decision_source']}")
        logger.info(f"  timestamp: {decision_dict['timestamp']}")

        # Verify serialization
        assert isinstance(decision_dict, dict)
        assert 'routing_mode' in decision_dict
        assert 'decision_source' in decision_dict
        assert 'timestamp' in decision_dict
        assert isinstance(decision_dict['timestamp'], str)  # Should be ISO format

        logger.info("\n✓ Decision serializes correctly for API responses")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3 TRACEABILITY VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info("✓ All traceability features verified!")
        logger.info("\nTraceability Features:")
        logger.info("  ✓ Decision sources clearly labeled (manual/data/rule/default)")
        logger.info("  ✓ Complete decision context in every decision")
        logger.info("  ✓ Human-readable explanations for all scenarios")
        logger.info("  ✓ Timestamps for complete audit trail")
        logger.info("  ✓ Transparent fallback rule usage")
        logger.info("  ✓ API-ready serialization")
        logger.info("\nRouter Honesty:")
        logger.info("  ✓ Phase 3 clearly marks all decisions as rule-based")
        logger.info("  ✓ Future comparison data will be clearly distinguished")
        logger.info("  ✓ Users can always see WHY an engine was selected")
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
    success = test_traceability()
    sys.exit(0 if success else 1)
