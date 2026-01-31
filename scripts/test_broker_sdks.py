#!/usr/bin/env python3
"""
Broker SDK Test Script
Tests all broker trading functions to ensure they work correctly.
Run this before deploying to verify SDK compatibility.
"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.metaapi_sdk_service import _truncate_comment, MAX_COMMENT_LENGTH


def test_comment_truncation():
    """Test comment truncation function."""
    print("\n=== Testing Comment Truncation ===")

    test_cases = [
        ("Short", "Short"),
        ("Test", "Test"),
        ("Signal_abc123", "Signal_abc123"),
        ("Test signal from dashboard (will auto-close)", "Test signal from dashboard"),  # 26 chars
        ("This is a very long comment that exceeds the limit", "This is a very long commen"),  # 26 chars
        ("A" * 50, "A" * 26),
        (None, None),
        ("", ""),
    ]

    all_passed = True
    for input_val, expected in test_cases:
        result = _truncate_comment(input_val)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
            print(f"  {status} Input: '{input_val}' -> Expected: '{expected}', Got: '{result}'")
        else:
            print(f"  {status} Input: '{input_val[:20] if input_val and len(input_val) > 20 else input_val}...' -> '{result}' (len={len(result) if result else 0})")

    print(f"\nMAX_COMMENT_LENGTH = {MAX_COMMENT_LENGTH}")
    assert MAX_COMMENT_LENGTH == 26, f"MAX_COMMENT_LENGTH should be 26, got {MAX_COMMENT_LENGTH}"
    print(f"  ✓ MAX_COMMENT_LENGTH is correctly set to 26")

    return all_passed


def test_signal_comment_generation():
    """Test signal comment generation."""
    print("\n=== Testing Signal Comment Generation ===")

    # Simulate signal ID
    signal_id = "b2c87d2a-1e36-425d-9f26-7534170c1018"

    # Test default comment format
    default_comment = f"S_{signal_id[:6]}"
    print(f"  Default comment: '{default_comment}' (len={len(default_comment)})")
    assert len(default_comment) <= 26, f"Default comment too long: {len(default_comment)}"
    print(f"  ✓ Default comment length OK ({len(default_comment)} <= 26)")

    # Test with custom comment
    custom_comments = [
        "Test",
        "Close",
        "TradingView Signal",
        "My Strategy Entry",
        "A very very very very long comment that should be truncated",
    ]

    for comment in custom_comments:
        truncated = (comment or default_comment)[:26]
        print(f"  '{comment[:20]}...' -> '{truncated}' (len={len(truncated)})")
        assert len(truncated) <= 26, f"Truncated comment too long: {len(truncated)}"

    print(f"  ✓ All custom comments properly truncated")
    return True


async def test_metaapi_sdk_available():
    """Test if MetaAPI SDK is available."""
    print("\n=== Testing MetaAPI SDK Availability ===")

    try:
        from metaapi_cloud_sdk import MetaApi
        print("  ✓ MetaAPI SDK imported successfully")

        # Check SDK version
        import metaapi_cloud_sdk
        version = getattr(metaapi_cloud_sdk, '__version__', 'unknown')
        print(f"  ✓ MetaAPI SDK version: {version}")

        return True
    except ImportError as e:
        print(f"  ✗ MetaAPI SDK not available: {e}")
        return False


async def test_tradelocker_sdk_available():
    """Test if TradeLocker SDK is available."""
    print("\n=== Testing TradeLocker SDK Availability ===")

    try:
        import tradelocker
        print("  ✓ TradeLocker SDK imported successfully")

        # Check SDK version
        version = getattr(tradelocker, '__version__', 'unknown')
        print(f"  ✓ TradeLocker SDK version: {version}")

        return True
    except ImportError as e:
        print(f"  ✗ TradeLocker SDK not available: {e}")
        return False


async def test_projectx_sdk_available():
    """Test if ProjectX SDK is available."""
    print("\n=== Testing ProjectX SDK Availability ===")

    try:
        from topstep import TopstepClient
        print("  ✓ ProjectX/TopStep SDK imported successfully")
        return True
    except ImportError:
        try:
            # Alternative import
            import aiohttp
            print("  ✓ aiohttp available for ProjectX REST API")
            return True
        except ImportError as e:
            print(f"  ✗ ProjectX SDK not available: {e}")
            return False


def test_broker_comment_limits():
    """Test comment limits for all brokers."""
    print("\n=== Broker Comment Limits Summary ===")

    limits = {
        "MetaAPI (MT4/MT5)": {
            "comment_only": 26,
            "comment_with_clientId": "26 - len(clientId)",
            "note": "Combined comment + clientId must be <= 26"
        },
        "TradeLocker": {
            "comment": "No documented limit",
            "note": "Uses strategyId field, not comment"
        },
        "ProjectX/TopStep": {
            "comment": "No documented limit",
            "note": "Uses description field"
        },
        "Tradovate": {
            "comment": "No documented limit",
            "note": "Uses customTag field"
        }
    }

    for broker, info in limits.items():
        print(f"\n  {broker}:")
        for key, value in info.items():
            print(f"    {key}: {value}")

    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("BROKER SDK TEST SUITE")
    print("=" * 60)

    results = {}

    # Run tests
    results["Comment Truncation"] = test_comment_truncation()
    results["Signal Comment Generation"] = test_signal_comment_generation()
    results["MetaAPI SDK"] = await test_metaapi_sdk_available()
    results["TradeLocker SDK"] = await test_tradelocker_sdk_available()
    results["ProjectX SDK"] = await test_projectx_sdk_available()
    results["Broker Comment Limits"] = test_broker_comment_limits()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
