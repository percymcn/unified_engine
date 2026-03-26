#!/usr/bin/env python3
"""
Seed Strategy Engines into Registry
====================================

Registers the 4 core strategy engines in the strategy registry database:
1. BREAKOUT ENGINE (breakout_v1)
2. TREND ENGINE (trend_v1)
3. MEAN REVERSION ENGINE (mean_reversion_v1)
4. LIQUIDITY REVERSAL ENGINE (liquidity_reversal_v1)

Usage:
    python scripts/seed_strategy_engines.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.strategy_registry_models import Strategy
from app.services.strategy_registry.schemas import StrategyStatus, StrategyType


def seed_engines(db: Session):
    """Seed the 4 core strategy engines into the registry."""

    engines = [
        {
            "strategy_id": "breakout_v1",
            "strategy_type": "breakout",
            "name": "Breakout Engine V1",
            "description": (
                "Compression + structural level breakouts. "
                "Detects volatility compression, identifies key structural levels "
                "(PDH, PDL, VWAP, pivots), and enters on volume-confirmed breakouts. "
                "Target: Next structural level or 2-3 ATR."
            ),
            "parameters": {
                "min_risk_reward": 1.5,
                "compression_threshold": 0.7,
                "volume_expansion_threshold": 1.3,
                "breakout_momentum_threshold": 0.6,
                "level_tolerance_pct": 0.003
            },
            "timeframe": "5m",
            "status": StrategyStatus.APPROVED_FOR_ROUTER,
            "is_active": True,
            "tags": ["breakout", "compression", "volume", "structural_levels"],
            "notes": "Phase 14: Core breakout strategy. Optimal for vol_expansion and vol_contraction regimes."
        },
        {
            "strategy_id": "trend_v1",
            "strategy_type": "trend",
            "name": "Trend Engine V1",
            "description": (
                "Pullback entries in sustained trends. "
                "Confirms trend via EMA alignment (9 > 21 > 50), waits for pullback to "
                "EMA21 or VWAP zone, enters on continuation confirmation. "
                "Target: 2.5 ATR or next structural level."
            ),
            "parameters": {
                "min_risk_reward": 1.5,
                "ema_fast_period": 9,
                "ema_mid_period": 21,
                "ema_slow_period": 50,
                "pullback_zone_width": 0.005,
                "min_ema_separation_pct": 0.2
            },
            "timeframe": "5m",
            "status": StrategyStatus.APPROVED_FOR_ROUTER,
            "is_active": True,
            "tags": ["trend", "pullback", "ema", "continuation"],
            "notes": "Phase 14: Core trend-following strategy. Optimal for trending_up and trending_down regimes."
        },
        {
            "strategy_id": "mean_reversion_v1",
            "strategy_type": "mean_reversion",
            "name": "Mean Reversion Engine V1",
            "description": (
                "Return to fair value in ranging markets. "
                "Detects ranging regime, identifies extremes via Bollinger Bands and RSI, "
                "enters on exhaustion signals with target of VWAP/BB middle. "
                "Only operates in non-trending conditions."
            ),
            "parameters": {
                "min_risk_reward": 1.5,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "vwap_deviation_threshold": 0.015,
                "bb_extreme_threshold": 0.1,
                "volume_exhaustion_threshold": 0.8
            },
            "timeframe": "5m",
            "status": StrategyStatus.APPROVED_FOR_ROUTER,
            "is_active": True,
            "tags": ["mean_reversion", "ranging", "bollinger", "rsi", "vwap"],
            "notes": "Phase 14: Core mean reversion strategy. Optimal for ranging and mean_reverting regimes."
        },
        {
            "strategy_id": "liquidity_reversal_v1",
            "strategy_type": "liquidity_reversal",
            "name": "Liquidity Reversal Engine V1",
            "description": (
                "False breakout / stop hunt reversals. "
                "Identifies equal highs/lows (liquidity pools), detects sweep beyond level, "
                "confirms reclaim with rejection wick. Fades retail breakouts. "
                "Target: Opposite side of range. Higher R:R requirement (2:1)."
            ),
            "parameters": {
                "min_risk_reward": 2.0,
                "equal_level_tolerance_pct": 0.002,
                "sweep_extension_pct": 0.001,
                "reclaim_confirmation_pct": 0.001,
                "min_wick_ratio": 0.4
            },
            "timeframe": "5m",
            "status": StrategyStatus.APPROVED_FOR_ROUTER,
            "is_active": True,
            "tags": ["liquidity", "reversal", "false_breakout", "stop_hunt", "counter_trend"],
            "notes": "Phase 14: Core liquidity reversal strategy. Optimal for chaotic and ranging regimes."
        }
    ]

    seeded_count = 0
    updated_count = 0

    for engine_data in engines:
        strategy_id = engine_data["strategy_id"]

        # Check if already exists
        existing = db.query(Strategy).filter(Strategy.strategy_id == strategy_id).first()

        if existing:
            # Update existing
            print(f"Updating existing strategy: {strategy_id}")

            existing.name = engine_data["name"]
            existing.description = engine_data["description"]
            existing.parameters = engine_data["parameters"]
            existing.timeframe = engine_data["timeframe"]
            existing.status = engine_data["status"]
            existing.is_active = engine_data["is_active"]
            existing.tags = engine_data["tags"]
            existing.notes = engine_data["notes"]
            existing.updated_at = datetime.now()

            updated_count += 1
        else:
            # Create new
            print(f"Creating new strategy: {strategy_id}")

            new_strategy = Strategy(
                strategy_id=strategy_id,
                strategy_type=engine_data["strategy_type"],
                name=engine_data["name"],
                description=engine_data["description"],
                parameters=engine_data["parameters"],
                timeframe=engine_data["timeframe"],
                status=engine_data["status"],
                is_active=engine_data["is_active"],
                tags=engine_data["tags"],
                notes=engine_data["notes"],
                # No parent_strategy_id - these are built-in engines, not variants
                parent_strategy_id=None,
                # No performance metrics yet - will be populated after backtesting
                sharpe_ratio=None,
                total_return_pct=None,
                max_drawdown_pct=None,
                win_rate=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            db.add(new_strategy)
            seeded_count += 1

    # Commit all changes
    db.commit()

    print(f"\n✅ Seeding complete:")
    print(f"   - Created: {seeded_count} strategies")
    print(f"   - Updated: {updated_count} strategies")
    print(f"   - Total: {seeded_count + updated_count} engines")

    # List all engines
    print("\n📋 Registered strategy engines:")
    all_engines = db.query(Strategy).filter(
        Strategy.strategy_id.in_([e["strategy_id"] for e in engines])
    ).all()

    for engine in all_engines:
        print(f"   - {engine.strategy_id} ({engine.strategy_type}): {engine.status.value}, active={engine.is_active}")


if __name__ == "__main__":
    print("🌱 Seeding 4 Core Strategy Engines...")
    print("-" * 60)

    db = SessionLocal()
    try:
        seed_engines(db)
    except Exception as e:
        print(f"\n❌ Error seeding engines: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    print("\n✨ Done!")
