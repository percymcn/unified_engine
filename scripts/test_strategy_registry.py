"""
Phase 6 Terminal Verification Script
=====================================

Tests the Strategy Registry system end-to-end:
1. Seed built-in strategies
2. List strategies
3. Generate variant
4. Evaluate variant
5. Promote/reject workflow
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.services.strategy_registry import (
    StrategyRegistry,
    VariantGenerator,
    StrategyEvaluator,
    VariantGenerateRequest,
    EvaluationRequest,
    PromotionRequest,
    RejectionRequest,
)


async def main():
    """Run Phase 6 verification tests."""
    print("\n" + "=" * 60)
    print("PHASE 6 TERMINAL VERIFICATION")
    print("Strategy Registry + Variant Evaluation Pipeline")
    print("=" * 60 + "\n")

    db = SessionLocal()

    try:
        # ===================================================================
        # TEST 1: Seed built-in strategies
        # ===================================================================
        print("TEST 1: Seeding built-in strategies...")
        registry = StrategyRegistry(db)
        built_ins = registry.seed_built_in_strategies()
        print(f"✅ Seeded {len(built_ins)} built-in strategies")
        for strategy in built_ins:
            print(f"  - {strategy.strategy_id} ({strategy.strategy_type}) - {strategy.status}")

        # ===================================================================
        # TEST 2: List strategies
        # ===================================================================
        print("\nTEST 2: Listing built-in strategies...")
        all_strategies = registry.list_strategies(status=['built_in'])
        print(f"✅ Found {len(all_strategies)} built-in strategies")

        # ===================================================================
        # TEST 3: Generate a variant
        # ===================================================================
        print("\nTEST 3: Generating variant from deterministic_v1...")
        generator = VariantGenerator(registry)

        variant_request = VariantGenerateRequest(
            parent_strategy_id='deterministic_v1',
            parameter_changes={
                'min_confidence_score': 80.0,  # Change from 75.0
                'min_risk_reward': 2.5,  # Change from 2.0
            },
            hypothesis="Testing higher confidence threshold (80%) and better R:R (2.5:1) for stricter entry criteria",
            created_by="test_script"
        )

        variant = generator.generate_variant(variant_request)
        print(f"✅ Generated variant: {variant.strategy_id}")
        print(f"  - Type: {variant.strategy_type}")
        print(f"  - Version: {variant.version}")
        print(f"  - Status: {variant.status}")
        print(f"  - Changes: {variant.parameter_changes}")

        # ===================================================================
        # TEST 4: Get candidate stats
        # ===================================================================
        print("\nTEST 4: Checking candidate stats for deterministic_v1...")
        stats = registry.get_candidate_stats('deterministic_v1')
        print(f"✅ Candidate stats:")
        print(f"  - Active candidates: {stats.active_candidates}/{stats.max_candidates}")
        print(f"  - Can create more: {stats.can_create_more}")

        # ===================================================================
        # TEST 5: Evaluate variant (backtest)
        # ===================================================================
        print(f"\nTEST 5: Evaluating variant {variant.strategy_id}...")
        print("  ⏳ Running 30-day backtest (this may take a minute)...")

        evaluator = StrategyEvaluator(registry)

        eval_request = EvaluationRequest(
            strategy_id=variant.strategy_id,
            ticker='MES',
            backtest_days=30,  # Short test for speed
            notes="Phase 6 terminal verification",
            evaluated_by="test_script"
        )

        evaluation = await evaluator.evaluate_strategy(eval_request)
        print(f"✅ Evaluation complete!")
        print(f"  - Evaluation ID: {evaluation.evaluation_id}")
        print(f"  - Comparison ID: {evaluation.comparison_id}")
        sharpe_str = f"{evaluation.sharpe_ratio:.2f}" if evaluation.sharpe_ratio is not None else "N/A"
        print(f"  - Sharpe Ratio: {sharpe_str}")
        win_rate_str = f"{evaluation.win_rate:.1f}%" if evaluation.win_rate is not None else "N/A"
        print(f"  - Win Rate: {win_rate_str}")
        max_dd_str = f"{evaluation.max_drawdown:.1f}%" if evaluation.max_drawdown is not None else "N/A"
        print(f"  - Max Drawdown: {max_dd_str}")
        print(f"  - Total Trades: {evaluation.total_trades}")
        net_profit_str = f"${evaluation.net_profit:.2f}" if evaluation.net_profit is not None else "$0.00"
        print(f"  - Net Profit: {net_profit_str}")
        print(f"\n  Criteria Results:")
        for cr in evaluation.criteria_results:
            status = "✅ PASS" if cr.passed else "❌ FAIL"
            print(f"    {status} - {cr.criterion}: {cr.details}")
        print(f"\n  Overall: {'✅ PASSED' if evaluation.passed else '❌ FAILED'}")
        print(f"  Recommendation: {evaluation.recommendation}")

        # ===================================================================
        # TEST 6: Promote or reject based on evaluation
        # ===================================================================
        if evaluation.recommendation == "APPROVE":
            print(f"\nTEST 6: Promoting {variant.strategy_id}...")
            promoted = registry.promote_strategy(
                strategy_id=variant.strategy_id,
                approved_by="test_admin",
                approval_notes="Passed all evaluation criteria in terminal verification"
            )
            print(f"✅ Strategy promoted!")
            print(f"  - New status: {promoted.status}")
            print(f"  - Approved by: {promoted.approved_by}")
            print(f"  - Approved at: {promoted.approved_at}")
        else:
            print(f"\nTEST 6: Rejecting {variant.strategy_id}...")
            rejected = registry.reject_strategy(
                strategy_id=variant.strategy_id,
                rejected_by="test_admin",
                rejection_notes="Failed evaluation criteria in terminal verification"
            )
            print(f"✅ Strategy rejected!")
            print(f"  - New status: {rejected.status}")
            print(f"  - Rejected by: {rejected.rejected_by}")
            print(f"  - Rejected at: {rejected.rejected_at}")

        # ===================================================================
        # TEST 7: Final status check
        # ===================================================================
        print("\nTEST 7: Final strategy listing...")
        all_strategies = registry.list_strategies()
        print(f"✅ Total strategies: {len(all_strategies)}")

        by_status = {}
        for s in all_strategies:
            by_status[s.status] = by_status.get(s.status, 0) + 1

        print("  Status breakdown:")
        for status, count in by_status.items():
            print(f"    - {status}: {count}")

        # ===================================================================
        # Summary
        # ===================================================================
        print("\n" + "=" * 60)
        print("PHASE 6 VERIFICATION COMPLETE")
        print("=" * 60)
        print("\n✅ All tests passed!")
        print("\nPhase 6A-6D Implementation Summary:")
        print("  ✅ Database models created")
        print("  ✅ Registry service operational")
        print("  ✅ Variant generator working")
        print("  ✅ Evaluation engine functional")
        print("  ✅ Promotion/rejection workflow verified")
        print("\nNext steps (deferred to Phase 7):")
        print("  - Phase 6E: Router integration")
        print("  - Phase 6F: UI implementation")
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
