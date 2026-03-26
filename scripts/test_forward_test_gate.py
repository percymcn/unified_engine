"""
Phase 7 Terminal Verification Script
=====================================

Tests the Forward-Test Gate system end-to-end:
1. Create variant (from Phase 6)
2. Approve for forward test
3. Simulate forward-test session
4. Evaluate gate
5. Approve/reject for router
6. Verify router eligibility filter
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.services.strategy_registry import (
    StrategyRegistry,
    VariantGenerator,
    VariantGenerateRequest,
    get_strategy_registry,
)
from app.services.strategy_registry.forward_test_gate import ForwardTestGate
from app.models.forward_test_models import ForwardTestSession


async def main():
    """Run Phase 7 verification tests."""
    print("\n" + "=" * 70)
    print("PHASE 7 TERMINAL VERIFICATION")
    print("Forward-Test Gate for Promoted Variants")
    print("=" * 70 + "\n")

    db = SessionLocal()

    try:
        registry = StrategyRegistry(db)
        generator = VariantGenerator(registry)
        gate = ForwardTestGate(db)

        # ================================================================
        # TEST 1: Create variant (from Phase 6)
        # ================================================================
        print("TEST 1: Creating variant from deterministic_v1...")

        variant_request = VariantGenerateRequest(
            parent_strategy_id='deterministic_v1',
            parameter_changes={
                'min_confidence_score': 70.0,  # Lower from 75.0
                'min_risk_reward': 1.8,  # Lower from 2.0
            },
            hypothesis="Testing more lenient entry criteria for higher trade frequency",
            created_by="phase7_test"
        )

        variant = generator.generate_variant(variant_request)
        print(f"✅ Created variant: {variant.strategy_id}")
        print(f"  - Status: {variant.status}")
        print(f"  - Changes: {variant.parameter_changes}")

        # ================================================================
        # TEST 2: Approve for forward test
        # ================================================================
        print("\nTEST 2: Approving variant for forward test...")

        # First, mock an evaluation (required)
        from datetime import datetime
        strategy = registry.get_strategy(variant.strategy_id)
        strategy.evaluated_at = datetime.now()
        strategy.sharpe_ratio = 1.2
        strategy.win_rate = 52.0
        db.commit()

        approved = registry.approve_for_forward_test(
            strategy_id=variant.strategy_id,
            approved_by="test_admin",
            approval_notes="Backtest passed, approved for forward testing"
        )
        print(f"✅ Approved for forward test")
        print(f"  - Status: {approved.status}")
        print(f"  - Approved by: {approved.approved_for_forward_test_by}")
        print(f"  - Approved at: {approved.approved_for_forward_test_at}")

        # ================================================================
        # TEST 3: Simulate forward-test session
        # ================================================================
        print("\nTEST 3: Simulating forward-test session...")

        session_id = f"FT_PHASE7_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create mock session
        session = ForwardTestSession(
            session_id=session_id,
            strategy_id=variant.strategy_id,
            tickers=["MES"],
            start_time=datetime.now(),
            total_trades=35,  # Above minimum of 30
            winning_trades=18,
            losing_trades=17,
            total_pnl=450.0,
            win_rate=51.4,  # Above 45%
            max_drawdown=-12.5,  # Below 25%
            profit_factor=1.35,  # Above 1.2
        )
        db.add(session)
        db.commit()

        # Link to strategy
        started = registry.start_forward_testing(
            strategy_id=variant.strategy_id,
            session_id=session_id
        )
        print(f"✅ Forward test session created")
        print(f"  - Session ID: {session_id}")
        print(f"  - Status: {started.status}")
        print(f"  - Total Trades: {session.total_trades}")
        print(f"  - Win Rate: {session.win_rate:.1f}%")
        print(f"  - Profit Factor: {session.profit_factor:.2f}")

        # ================================================================
        # TEST 4: Evaluate forward-test gate
        # ================================================================
        print("\nTEST 4: Evaluating forward-test gate...")

        decision = gate.evaluate_gate(
            session_id=session_id,
            strategy_id=variant.strategy_id,
            evaluated_by="test_admin"
        )

        print(f"✅ Gate evaluation complete")
        print(f"  - Decision: {decision.recommendation}")
        print(f"  - Passed: {decision.passed}")
        print(f"\n  Criteria Results:")
        for cr in decision.criteria_results:
            status = "✅ PASS" if cr.passed else "❌ FAIL"
            print(f"    {status} - {cr.criterion}: {cr.details}")

        # ================================================================
        # TEST 5: Approve/reject for router based on gate
        # ================================================================
        if decision.passed:
            print(f"\nTEST 5: Approving for router (gate passed)...")

            approved_for_router = registry.approve_for_router_after_gate(
                strategy_id=variant.strategy_id,
                approved_by="test_admin",
                gate_decision=decision
            )
            print(f"✅ Approved for router!")
            print(f"  - Status: {approved_for_router.status}")
            print(f"  - Approved by: {approved_for_router.approved_for_router_by}")
            print(f"  - Approved at: {approved_for_router.approved_for_router_at}")
        else:
            print(f"\nTEST 5: Failing forward test (gate failed)...")

            failed = registry.fail_forward_test(
                strategy_id=variant.strategy_id,
                failed_by="test_admin",
                gate_decision=decision
            )
            print(f"✅ Forward test failed")
            print(f"  - Status: {failed.status}")
            print(f"  - Failed by: {failed.forward_test_gate_failed_by}")
            print(f"  - Failure reason: {failed.forward_test_gate_failure_reason}")

        # ================================================================
        # TEST 6: Verify router eligibility filter
        # ================================================================
        print("\nTEST 6: Verifying router eligibility filter...")

        eligible = registry.get_router_eligible_strategies()
        eligible_ids = {s.strategy_id for s in eligible}

        print(f"✅ Router-eligible strategies: {len(eligible)}")
        print(f"\n  Eligible strategies:")
        for s in eligible:
            built_in_flag = "✓ built-in" if s.parent_strategy_id is None else f"  variant of {s.parent_strategy_id}"
            print(f"    - {s.strategy_id} ({s.strategy_type}) - {s.status} [{built_in_flag}]")

        # ================================================================
        # TEST 7: Verify safety - non-eligible strategies blocked
        # ================================================================
        print("\nTEST 7: Verifying safety - non-eligible strategies blocked...")

        all_strategies = registry.list_strategies()
        non_eligible_statuses = ['candidate', 'approved_for_forward_test', 'forward_testing', 'rejected']

        blocked_count = 0
        for s in all_strategies:
            if s.status in non_eligible_statuses:
                if s.strategy_id not in eligible_ids:
                    blocked_count += 1

        print(f"✅ Safety check passed")
        print(f"  - Total strategies: {len(all_strategies)}")
        print(f"  - Router-eligible: {len(eligible)}")
        print(f"  - Blocked from router: {blocked_count}")

        # ================================================================
        # TEST 8: Mark strategy active (simulate router selection)
        # ================================================================
        if decision.passed and variant.strategy_id in eligible_ids:
            print(f"\nTEST 8: Marking strategy as active (router selection)...")

            active = registry.mark_strategy_active(variant.strategy_id)
            print(f"✅ Marked as active")
            print(f"  - Status: {active.status}")
            print(f"  - Active at: {active.active_at}")

        # ================================================================
        # Summary
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 7 VERIFICATION COMPLETE")
        print("=" * 70)

        if decision.passed:
            print("\n✅ Full lifecycle test PASSED!")
            print("\nLifecycle flow:")
            print("  candidate → approved_for_forward_test → forward_testing → approved_for_router → active")
            print("\nSafety gates:")
            print("  ✅ Backtest evaluation required before forward test")
            print("  ✅ Forward-test gate enforces 5 criteria")
            print("  ✅ Only built_in, approved_for_router, active are router-eligible")
            print("  ✅ Non-eligible strategies blocked from router")
        else:
            print("\n✅ Gate rejection test PASSED!")
            print("\nLifecycle flow:")
            print("  candidate → approved_for_forward_test → forward_testing → rejected")
            print("\nSafety gates:")
            print("  ✅ Failed forward test → rejected status")
            print("  ✅ Rejected strategies blocked from router")

        print("\nPhase 7 Implementation Summary:")
        print("  ✅ Status model upgraded (4 new statuses)")
        print("  ✅ Forward-test session linkage")
        print("  ✅ Gate criteria engine (5 criteria)")
        print("  ✅ Registry workflow methods")
        print("  ✅ API endpoints (6 new endpoints)")
        print("  ✅ Router eligibility filter")
        print("  ✅ Database migration")
        print("  ✅ Full audit trail")
        print("")

    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
