#!/usr/bin/env python3
"""
Test OpenClaw Integration with SmartFlow
=========================================

Tests the OpenClaw signal validation system.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.openclaw_client import get_openclaw_client
from app.services.rsi_calculator import get_rsi_calculator


async def test_signal_analysis():
    """Test OpenClaw signal analysis"""
    print("🤖 Testing OpenClaw Signal Analysis")
    print("=" * 60)

    openclaw = get_openclaw_client()

    # Test Case 1: Strong bullish signal with good RSI
    print("\n📊 Test 1: STRONG BULLISH (should APPROVE)")
    result = await openclaw.analyze_signal(
        symbol="SPY",
        direction="long",
        flow_score=15.0,
        rsi=45.0,  # Good for long
        price=450.00,
        volume=1000000,
        flow_data={
            'sources': ['unusual_whales', 'floalgo'],
            'bullish_count': 20,
            'bearish_count': 3,
            'golden_sweeps': 2,
            'institutional': True
        }
    )
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Should Trade: {result['should_trade']}")
    print(f"  Entry: {result['entry_suggestion']}")
    print(f"  Reasoning: {result['reasoning']}")

    # Test Case 2: Weak signal with bad RSI
    print("\n📊 Test 2: WEAK SIGNAL (should REJECT)")
    result = await openclaw.analyze_signal(
        symbol="SPY",
        direction="long",
        flow_score=5.0,  # Weak flow
        rsi=75.0,  # Bad for long (overbought)
        price=450.00,
        volume=500000,
        flow_data={
            'sources': ['floalgo'],
            'bullish_count': 3,
            'bearish_count': 2,
            'golden_sweeps': 0,
            'institutional': False
        }
    )
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Should Trade: {result['should_trade']}")
    print(f"  Entry: {result['entry_suggestion']}")
    print(f"  Reasoning: {result['reasoning']}")

    # Test Case 3: Good short signal
    print("\n📊 Test 3: SHORT SIGNAL (should APPROVE)")
    result = await openclaw.analyze_signal(
        symbol="QQQ",
        direction="short",
        flow_score=-12.0,
        rsi=65.0,  # Good for short
        price=380.00,
        volume=800000,
        flow_data={
            'sources': ['unusual_whales'],
            'bullish_count': 5,
            'bearish_count': 15,
            'golden_sweeps': 1,
            'institutional': True
        }
    )
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Should Trade: {result['should_trade']}")
    print(f"  Entry: {result['entry_suggestion']}")
    print(f"  Reasoning: {result['reasoning']}")

    await openclaw.close()


async def test_rsi_calculation():
    """Test RSI calculator"""
    print("\n\n📈 Testing RSI Calculator")
    print("=" * 60)

    rsi_calc = get_rsi_calculator()

    # Mock price data (14 days + 1)
    price_data = [
        {'close': 100.0},
        {'close': 102.0},
        {'close': 101.5},
        {'close': 103.0},
        {'close': 104.0},
        {'close': 103.5},
        {'close': 105.0},
        {'close': 106.0},
        {'close': 105.5},
        {'close': 107.0},
        {'close': 108.0},
        {'close': 107.5},
        {'close': 109.0},
        {'close': 110.0},
        {'close': 109.5},
    ]

    rsi = await rsi_calc.get_rsi("TEST", period=14, price_data=price_data)
    print(f"\n  RSI for TEST: {rsi:.2f}")
    print(f"  Interpretation: ", end="")

    if rsi < 30:
        print("OVERSOLD ⬇️")
    elif rsi > 70:
        print("OVERBOUGHT ⬆️")
    else:
        print("NEUTRAL ↔️")


async def main():
    """Run all tests"""
    try:
        await test_signal_analysis()
        await test_rsi_calculation()

        print("\n\n✅ All tests completed!")
        print("\n💡 Next Steps:")
        print("  1. Deploy updated SmartFlow service")
        print("  2. Monitor logs for OpenClaw validation")
        print("  3. Check for 🤖 [OPENCLAW APPROVED/BLOCKED] messages")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
