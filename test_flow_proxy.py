#!/usr/bin/env python3
"""
Test script for FlowAlgo Confluence Webhook Proxy

Usage:
    python3 test_flow_proxy.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:9001"


def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing /health endpoint...")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")

        if response.json().get('logged_in'):
            print("✓ Scraper is logged in")
        else:
            print("✗ Scraper NOT logged in - check credentials")

        return response.status_code == 200
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_recent_flow():
    """Test recent flow endpoint"""
    print("\n" + "=" * 60)
    print("Testing /recent endpoint...")
    print("=" * 60)

    try:
        # Test all tickers
        response = requests.get(f"{BASE_URL}/recent?minutes=10", timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Found {data['count']} flow entries in last 10 minutes")

        if data['count'] > 0:
            print("\nLatest entries:")
            for entry in data['entries'][:5]:
                print(f"  {entry['ticker']} {entry['side']} {entry['type']} "
                      f"${entry['premium']:,.0f} {entry['flow_type']}")
            print("✓ Flow data is being scraped")
        else:
            print("⚠ No flow entries found - scraper may be starting up or no qualifying flows")

        # Test specific ticker
        print("\nChecking SPY flow...")
        response = requests.get(f"{BASE_URL}/recent?ticker=SPY&minutes=5", timeout=5)
        data = response.json()
        print(f"SPY: {data['count']} entries in last 5 minutes")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_filter_webhook():
    """Test filter webhook endpoint"""
    print("\n" + "=" * 60)
    print("Testing /filter endpoint...")
    print("=" * 60)

    test_cases = [
        {
            "name": "MES BUY (should map to SPY)",
            "payload": {
                "ticker": "MES",
                "action": "buy",
                "price": 5500,
                "timestamp": "2026-03-05T12:00:00Z"
            }
        },
        {
            "name": "NQ SELL (should map to QQQ)",
            "payload": {
                "ticker": "NQ",
                "action": "sell",
                "price": 18000,
                "timestamp": "2026-03-05T12:00:00Z"
            }
        },
        {
            "name": "GC BUY (should map to GLD)",
            "payload": {
                "ticker": "GC",
                "action": "buy",
                "price": 2000,
                "timestamp": "2026-03-05T12:00:00Z"
            }
        },
        {
            "name": "Invalid ticker (should skip)",
            "payload": {
                "ticker": "AAPL",
                "action": "buy",
                "price": 150
            }
        }
    ]

    for test in test_cases:
        print(f"\n{test['name']}")
        print(f"Payload: {json.dumps(test['payload'], indent=2)}")

        try:
            response = requests.post(
                f"{BASE_URL}/filter",
                json=test['payload'],
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            print(f"Status: {response.status_code}")
            result = response.json()
            print(f"Response:\n{json.dumps(result, indent=2)}")

            status = result.get('status')
            if status == 'forwarded':
                print("✓ Signal FORWARDED (confluence detected)")
            elif status == 'skipped':
                print(f"⊘ Signal SKIPPED: {result.get('reason')}")
            else:
                print(f"? Unknown status: {status}")

        except Exception as e:
            print(f"✗ Failed: {e}")

        time.sleep(1)

    return True


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║   FlowAlgo Confluence Webhook Proxy - Test Suite          ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Check if service is running
    print("Checking if service is running...")
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
        print("✓ Service is running\n")
    except:
        print("✗ Service is NOT running!")
        print("\nStart it with:")
        print("  python3 flow_confluence_proxy.py")
        print("OR")
        print("  sudo systemctl start flow_confluence_proxy")
        return

    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    time.sleep(2)
    results.append(("Recent Flow", test_recent_flow()))
    time.sleep(2)
    results.append(("Filter Webhook", test_filter_webhook()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Proxy is working correctly.")
        print("\nNext steps:")
        print("1. Configure your TradingView webhook URL to: http://your-ip:8080/filter")
        print("2. Update MYTRADEFLOW_WEBHOOK in .env to your actual webhook")
        print("3. Monitor logs: tail -f confluence.log")
    else:
        print("\n✗ Some tests failed. Check the output above for details.")


if __name__ == '__main__':
    main()
