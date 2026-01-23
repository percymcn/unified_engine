#!/usr/bin/env python3
"""
Broker Auth Smoke Test

Tests broker authentication without placing trades.
Reads credentials from environment variables only.

Usage:
    python3 scripts/broker_auth_smoke.py [broker]
    
Brokers: mt4, mt5, tradelocker, tradovate, projectx, all

Environment Variables (per broker):
    MT4_* / MT5_*:
        MT4_API_KEY, MT4_API_SECRET, MT4_ACCOUNT_NUMBER
        MT5_API_KEY, MT5_API_SECRET, MT5_ACCOUNT_NUMBER
    
    TRADELOCKER_*:
        TRADELOCKER_API_KEY, TRADELOCKER_API_SECRET
        TRADELOCKER_USERNAME (optional, for Brand API)
    
    TRADOVATE_*:
        TRADOVATE_ACCESS_TOKEN (OAuth token)
        TRADOVATE_ACCOUNT_ID
    
    PROJECTX_*:
        PROJECTX_API_KEY, PROJECTX_API_SECRET
        PROJECTX_ACCOUNT_ID
"""

import asyncio
import os
import sys
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.brokers.mt4_executor import MT4Executor
    from app.brokers.mt5_executor import MT5Executor
    from app.brokers.tradelocker_executor import TradeLockerExecutor
    from app.brokers.tradovate_executor import TradovateExecutor
    from app.brokers.projectx_executor import ProjectXExecutor
except ImportError as e:
    print(f"❌ ERROR: Failed to import broker executors: {e}")
    print("   Make sure you're running from project root with PYTHONPATH set")
    sys.exit(1)


def get_mt4_config() -> Optional[Dict[str, Any]]:
    """Get MT4 config from env vars"""
    api_key = os.getenv("MT4_API_KEY")
    api_secret = os.getenv("MT4_API_SECRET")
    account_number = os.getenv("MT4_ACCOUNT_NUMBER")
    
    if not all([api_key, api_secret, account_number]):
        return None
    
    return {
        "broker": "mt4",
        "api_key": api_key,
        "api_secret": api_secret,
        "account_number": account_number,
    }


def get_mt5_config() -> Optional[Dict[str, Any]]:
    """Get MT5 config from env vars"""
    api_key = os.getenv("MT5_API_KEY")
    api_secret = os.getenv("MT5_API_SECRET")
    account_number = os.getenv("MT5_ACCOUNT_NUMBER")
    
    if not all([api_key, api_secret, account_number]):
        return None
    
    return {
        "broker": "mt5",
        "api_key": api_key,
        "api_secret": api_secret,
        "account_number": account_number,
    }


def get_tradelocker_config() -> Optional[Dict[str, Any]]:
    """Get TradeLocker config from env vars"""
    api_key = os.getenv("TRADELOCKER_API_KEY")
    api_secret = os.getenv("TRADELOCKER_API_SECRET")
    username = os.getenv("TRADELOCKER_USERNAME")
    
    if not all([api_key, api_secret]):
        return None
    
    config = {
        "broker": "tradelocker",
        "api_key": api_key,
        "api_secret": api_secret,
    }
    
    if username:
        config["username"] = username
    
    return config


def get_tradovate_config() -> Optional[Dict[str, Any]]:
    """Get Tradovate config from env vars"""
    access_token = os.getenv("TRADOVATE_ACCESS_TOKEN")
    account_id = os.getenv("TRADOVATE_ACCOUNT_ID")
    
    if not access_token:
        return None
    
    config = {
        "broker": "tradovate",
        "access_token": access_token,
    }
    
    if account_id:
        config["account_id"] = account_id
    
    return config


def get_projectx_config() -> Optional[Dict[str, Any]]:
    """Get ProjectX config from env vars"""
    api_key = os.getenv("PROJECTX_API_KEY")
    api_secret = os.getenv("PROJECTX_API_SECRET")
    account_id = os.getenv("PROJECTX_ACCOUNT_ID")
    
    if not all([api_key, api_secret]):
        return None
    
    config = {
        "broker": "projectx",
        "api_key": api_key,
        "api_secret": api_secret,
    }
    
    if account_id:
        config["account_id"] = account_id
    
    return config


async def test_broker_auth(broker_name: str, executor_class, get_config_func) -> tuple[bool, str]:
    """
    Test broker authentication.
    
    Returns:
        (success: bool, message: str)
    """
    print(f"\n--- Testing {broker_name.upper()} ---")
    
    # Get config
    config = get_config_func()
    if not config:
        return False, f"SKIP: Missing environment variables (check {broker_name.upper()}_*)"
    
    try:
        # Create executor
        executor = executor_class(config)
        
        # Test authenticate
        print(f"  [1/3] Authenticating...")
        auth_result = await executor.authenticate()
        if not auth_result:
            return False, "FAIL: authenticate() returned False"
        print(f"        ✅ Authentication successful")
        
        # Test connect
        print(f"  [2/3] Connecting...")
        connect_result = await executor.connect()
        if not connect_result:
            return False, "FAIL: connect() returned False"
        print(f"        ✅ Connection successful")
        
        # Test get_account_info (minimal read-only operation)
        print(f"  [3/3] Fetching account info...")
        try:
            account_info = await executor.get_account_info()
            if not account_info:
                return False, "FAIL: get_account_info() returned empty"
            
            # Print minimal info (don't expose sensitive data)
            balance = account_info.get("balance", "N/A")
            equity = account_info.get("equity", "N/A")
            print(f"        ✅ Account info retrieved")
            print(f"        Balance: {balance}, Equity: {equity}")
            
        except Exception as e:
            return False, f"FAIL: get_account_info() raised exception: {str(e)}"
        
        # Cleanup
        try:
            await executor.disconnect()
        except:
            pass
        
        return True, "PASS: All checks passed"
        
    except Exception as e:
        return False, f"FAIL: Exception during test: {str(e)}"


async def main():
    broker_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    broker_arg = broker_arg.lower()
    
    tests = []
    
    if broker_arg in ["all", "mt4"]:
        tests.append(("MT4", MT4Executor, get_mt4_config))
    
    if broker_arg in ["all", "mt5"]:
        tests.append(("MT5", MT5Executor, get_mt5_config))
    
    if broker_arg in ["all", "tradelocker"]:
        tests.append(("TradeLocker", TradeLockerExecutor, get_tradelocker_config))
    
    if broker_arg in ["all", "tradovate"]:
        tests.append(("Tradovate", TradovateExecutor, get_tradovate_config))
    
    if broker_arg in ["all", "projectx"]:
        tests.append(("ProjectX", ProjectXExecutor, get_projectx_config))
    
    if not tests:
        print(f"❌ ERROR: Unknown broker '{broker_arg}'")
        print("   Valid brokers: mt4, mt5, tradelocker, tradovate, projectx, all")
        sys.exit(1)
    
    results = []
    
    for broker_name, executor_class, get_config_func in tests:
        success, message = await test_broker_auth(broker_name, executor_class, get_config_func)
        results.append((broker_name, success, message))
        print(f"  Result: {message}")
    
    # Summary
    print("\n=== Summary ===")
    passed = sum(1 for _, success, _ in results if success)
    skipped = sum(1 for _, success, msg in results if not success and "SKIP" in msg)
    failed = len(results) - passed - skipped
    
    for broker_name, success, message in results:
        status = "✅" if success else ("⏭️ " if "SKIP" in message else "❌")
        print(f"{status} {broker_name}: {message}")
    
    print(f"\nTotal: {passed} passed, {skipped} skipped, {failed} failed")
    
    # Exit with error if any failed
    if failed > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
