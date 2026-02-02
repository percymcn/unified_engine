#!/usr/bin/env python3
"""
Comprehensive Trading Functions Test Suite
Tests all broker executors and trading functions without placing real trades.

Usage:
    DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db" python3 scripts/test_trading_functions.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.database_models import TradingAccount, BrokerType, Credential
from app.core.encryption import get_encryption_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results storage
test_results: Dict[str, Dict[str, Any]] = {}


def record_result(broker: str, test_name: str, success: bool, message: str = "", data: Any = None):
    """Record a test result."""
    if broker not in test_results:
        test_results[broker] = {"tests": [], "passed": 0, "failed": 0}

    result = {
        "test": test_name,
        "success": success,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    test_results[broker]["tests"].append(result)

    if success:
        test_results[broker]["passed"] += 1
        logger.info(f"✅ [{broker}] {test_name}: {message}")
    else:
        test_results[broker]["failed"] += 1
        logger.error(f"❌ [{broker}] {test_name}: {message}")


def load_credentials(db: Session, account: TradingAccount) -> Dict[str, Any]:
    """Load decrypted credentials for a trading account."""
    credentials: Dict[str, Any] = {}
    encryption = get_encryption_service()
    broker_value = account.broker.value

    # OAuth tokens from account
    if account.access_token:
        credentials["access_token"] = account.access_token
    if account.refresh_token:
        credentials["refresh_token"] = account.refresh_token
    if account.oauth_environment:
        credentials["environment"] = account.oauth_environment

    if credentials.get("access_token"):
        credentials["account_id"] = account.account_number
        return credentials

    # Load from Credential table
    rows = db.query(Credential).filter(
        Credential.user_id == account.user_id,
        Credential.service == broker_value,
        Credential.is_active == True
    ).all()

    for row in rows:
        try:
            data = encryption.decrypt_dict(row.encrypted_data)
            credentials.update(data)
        except Exception as e:
            logger.warning(f"Failed to decrypt credential {row.id}: {e}")

    credentials["account_id"] = account.account_number
    if account.default_broker_account_id:
        credentials["broker_account_id"] = account.default_broker_account_id

    # MT4/MT5 extra metadata
    if account.broker and account.broker.value in ("mt4", "mt5"):
        if account.extra_metadata and isinstance(account.extra_metadata, dict):
            if account.extra_metadata.get("metaapi_account_id"):
                credentials["metaapi_account_id"] = account.extra_metadata["metaapi_account_id"]

    return credentials


async def test_tradelocker(account: TradingAccount, credentials: Dict[str, Any]) -> None:
    """Test TradeLocker executor functions."""
    broker = "tradelocker"

    try:
        from app.brokers.tradelocker_executor import TradeLockerExecutor

        # Check credentials
        if not credentials.get("username") or not credentials.get("password") or not credentials.get("server"):
            record_result(broker, "credentials_check", False, "Missing username, password, or server")
            return

        record_result(broker, "credentials_check", True, "Credentials available")

        # Normalize environment
        raw_env = credentials.get("sdk_environment") or credentials.get("environment", "https://demo.tradelocker.com")
        if raw_env and not raw_env.startswith("http"):
            if raw_env.lower() in ("demo", "live"):
                raw_env = f"https://{raw_env.lower()}.tradelocker.com"
            else:
                raw_env = f"https://{raw_env}.tradelocker.com"

        # Create executor
        executor = TradeLockerExecutor(
            username=credentials.get("username"),
            password=credentials.get("password"),
            server=credentials.get("server"),
            sdk_environment=raw_env,
            account_id=credentials.get("broker_account_id"),
            account_num=credentials.get("account_num"),
        )

        record_result(broker, "executor_create", True, "Executor created")

        # Initialize
        try:
            init_result = await asyncio.wait_for(executor.initialize(), timeout=30.0)
            if init_result:
                record_result(broker, "initialize", True, "Connected successfully")
            else:
                record_result(broker, "initialize", False, "Initialize returned False")
                return
        except asyncio.TimeoutError:
            record_result(broker, "initialize", False, "Connection timed out (30s)")
            return
        except Exception as e:
            record_result(broker, "initialize", False, f"Connection error: {e}")
            return

        # Test get_accounts
        try:
            accounts = await asyncio.wait_for(executor.get_accounts(), timeout=15.0)
            record_result(broker, "get_accounts", True, f"Found {len(accounts)} accounts",
                         [{"id": a.id, "balance": a.balance} for a in accounts[:3]])
        except Exception as e:
            record_result(broker, "get_accounts", False, f"Error: {e}")

        # Test get_positions
        try:
            positions = await asyncio.wait_for(executor.get_positions(), timeout=15.0)
            record_result(broker, "get_positions", True, f"Found {len(positions)} positions",
                         [{"symbol": p.symbol, "size": p.size} for p in positions[:5]])
        except Exception as e:
            record_result(broker, "get_positions", False, f"Error: {e}")

        # Test get_instruments (if available)
        try:
            if hasattr(executor, 'get_instruments'):
                instruments = await asyncio.wait_for(executor.get_instruments(), timeout=15.0)
                record_result(broker, "get_instruments", True, f"Found {len(instruments)} instruments")
            else:
                record_result(broker, "get_instruments", True, "Method not available (OK)")
        except Exception as e:
            record_result(broker, "get_instruments", False, f"Error: {e}")

        # Cleanup
        try:
            await executor.disconnect()
            record_result(broker, "disconnect", True, "Disconnected cleanly")
        except Exception as e:
            record_result(broker, "disconnect", False, f"Error: {e}")

    except ImportError as e:
        record_result(broker, "import", False, f"Import error: {e}")
    except Exception as e:
        record_result(broker, "general", False, f"Unexpected error: {e}")


async def test_mt5(account: TradingAccount, credentials: Dict[str, Any]) -> None:
    """Test MT5 executor functions."""
    broker = "mt5"

    try:
        from app.brokers.mt5_executor import MT5Executor
        from app.core.config import settings

        # Check credentials
        metaapi_account_id = credentials.get("metaapi_account_id")
        metaapi_token = credentials.get("metaapi_token") or credentials.get("api_token") or getattr(settings, 'METAAPI_TOKEN', None)

        if not metaapi_account_id:
            record_result(broker, "credentials_check", False, "Missing metaapi_account_id")
            return
        if not metaapi_token:
            record_result(broker, "credentials_check", False, "Missing metaapi_token")
            return

        record_result(broker, "credentials_check", True, f"Credentials available (account_id: {metaapi_account_id[:8]}...)")

        # Create executor
        executor = MT5Executor(
            metaapi_token=metaapi_token,
            metaapi_account_id=metaapi_account_id,
        )

        record_result(broker, "executor_create", True, "Executor created")

        # Initialize
        try:
            init_result = await asyncio.wait_for(executor.initialize(), timeout=60.0)
            if init_result:
                record_result(broker, "initialize", True, f"Connected (SDK: {executor.is_using_sdk}, REST: {executor.is_using_rest_api})")
            else:
                record_result(broker, "initialize", False, "Initialize returned False")
                return
        except asyncio.TimeoutError:
            record_result(broker, "initialize", False, "Connection timed out (60s)")
            return
        except Exception as e:
            record_result(broker, "initialize", False, f"Connection error: {e}")
            return

        # Test get_accounts
        try:
            accounts = await asyncio.wait_for(executor.get_accounts(), timeout=15.0)
            record_result(broker, "get_accounts", True, f"Found {len(accounts)} accounts",
                         [{"id": a.id, "balance": a.balance, "equity": a.equity} for a in accounts[:3]])
        except Exception as e:
            record_result(broker, "get_accounts", False, f"Error: {e}")

        # Test get_positions
        try:
            positions = await asyncio.wait_for(executor.get_positions(), timeout=15.0)
            record_result(broker, "get_positions", True, f"Found {len(positions)} positions",
                         [{"symbol": p.symbol, "size": p.size, "pnl": p.unrealized_pnl} for p in positions[:5]])
        except Exception as e:
            record_result(broker, "get_positions", False, f"Error: {e}")

        # Test get_quote
        try:
            quote = await asyncio.wait_for(executor.get_quote("EURUSD"), timeout=10.0)
            if quote:
                record_result(broker, "get_quote", True, f"EURUSD quote: {quote}")
            else:
                record_result(broker, "get_quote", False, "No quote returned")
        except Exception as e:
            record_result(broker, "get_quote", False, f"Error: {e}")

        # Cleanup
        try:
            await executor.disconnect()
            record_result(broker, "disconnect", True, "Disconnected cleanly")
        except Exception as e:
            record_result(broker, "disconnect", False, f"Error: {e}")

    except ImportError as e:
        record_result(broker, "import", False, f"Import error: {e}")
    except Exception as e:
        record_result(broker, "general", False, f"Unexpected error: {e}")


async def test_projectx(account: TradingAccount, credentials: Dict[str, Any]) -> None:
    """Test ProjectX/TopStep executor functions."""
    broker = "projectx"

    try:
        from app.brokers.projectx_executor import ProjectXExecutor

        # Check credentials
        if not credentials.get("username") or not credentials.get("api_key"):
            record_result(broker, "credentials_check", False, "Missing username or api_key")
            return

        record_result(broker, "credentials_check", True, f"Credentials available (user: {credentials.get('username')})")

        # Create executor
        executor = ProjectXExecutor(
            username=credentials.get("username"),
            api_key=credentials.get("api_key"),
        )

        record_result(broker, "executor_create", True, "Executor created")

        # Initialize
        try:
            init_result = await asyncio.wait_for(executor.initialize(), timeout=30.0)
            if init_result:
                record_result(broker, "initialize", True, f"Connected (SDK mode: {executor.is_using_sdk})")
            else:
                record_result(broker, "initialize", False, "Initialize returned False")
                return
        except asyncio.TimeoutError:
            record_result(broker, "initialize", False, "Connection timed out (30s)")
            return
        except Exception as e:
            record_result(broker, "initialize", False, f"Connection error: {e}")
            return

        # Test get_accounts
        try:
            accounts = await asyncio.wait_for(executor.get_accounts(limit=5), timeout=15.0)
            record_result(broker, "get_accounts", True, f"Found {len(accounts)} accounts",
                         [{"id": a.id, "balance": a.balance, "status": a.extra_data.get('status') if a.extra_data else 'unknown'} for a in accounts[:3]])
        except Exception as e:
            record_result(broker, "get_accounts", False, f"Error: {e}")

        # Test get_positions
        try:
            positions = await asyncio.wait_for(executor.get_positions(), timeout=15.0)
            record_result(broker, "get_positions", True, f"Found {len(positions)} positions",
                         [{"symbol": p.symbol, "size": p.size, "side": p.side} for p in positions[:5]])
        except Exception as e:
            record_result(broker, "get_positions", False, f"Error: {e}")

        # Test get_symbols
        try:
            symbols = await asyncio.wait_for(executor.get_symbols(), timeout=15.0)
            record_result(broker, "get_symbols", True, f"Found {len(symbols)} symbols", symbols[:10])
        except Exception as e:
            record_result(broker, "get_symbols", False, f"Error: {e}")

        # Test get_quote (if SDK mode)
        if executor.is_using_sdk:
            try:
                quote = await asyncio.wait_for(executor.get_quote("MNQ"), timeout=10.0)
                if quote:
                    record_result(broker, "get_quote", True, f"MNQ quote: {quote}")
                else:
                    record_result(broker, "get_quote", True, "No quote data (market may be closed)")
            except Exception as e:
                record_result(broker, "get_quote", False, f"Error: {e}")

        # Cleanup
        try:
            await executor.disconnect()
            record_result(broker, "disconnect", True, "Disconnected cleanly")
        except Exception as e:
            record_result(broker, "disconnect", False, f"Error: {e}")

    except ImportError as e:
        record_result(broker, "import", False, f"Import error: {e}")
    except Exception as e:
        record_result(broker, "general", False, f"Unexpected error: {e}")


async def test_tradovate(account: TradingAccount, credentials: Dict[str, Any]) -> None:
    """Test Tradovate executor functions."""
    broker = "tradovate"

    try:
        from app.brokers.tradovate_executor import TradovateExecutor

        # Check credentials
        if not credentials.get("access_token"):
            record_result(broker, "credentials_check", False, "Missing access_token (OAuth required)")
            return

        record_result(broker, "credentials_check", True, "OAuth token available")

        # Create executor
        environment = credentials.get("environment") or account.oauth_environment or "demo"
        executor = TradovateExecutor(
            account_id=account.id,
            access_token=credentials.get("access_token"),
            environment=environment,
        )

        record_result(broker, "executor_create", True, f"Executor created (env: {environment})")

        # Initialize
        try:
            init_result = await asyncio.wait_for(executor.initialize(), timeout=30.0)
            if init_result:
                record_result(broker, "initialize", True, "Connected successfully")
            else:
                record_result(broker, "initialize", False, "Initialize returned False (token may be expired)")
                return
        except asyncio.TimeoutError:
            record_result(broker, "initialize", False, "Connection timed out (30s)")
            return
        except Exception as e:
            record_result(broker, "initialize", False, f"Connection error: {e}")
            return

        # Test get_accounts
        try:
            accounts = await asyncio.wait_for(executor.get_accounts(), timeout=15.0)
            record_result(broker, "get_accounts", True, f"Found {len(accounts)} accounts",
                         [{"id": a.id, "balance": a.balance} for a in accounts[:3]])
        except Exception as e:
            record_result(broker, "get_accounts", False, f"Error: {e}")

        # Test get_positions
        try:
            positions = await asyncio.wait_for(executor.get_positions(), timeout=15.0)
            record_result(broker, "get_positions", True, f"Found {len(positions)} positions",
                         [{"symbol": p.symbol, "size": p.size} for p in positions[:5]])
        except Exception as e:
            record_result(broker, "get_positions", False, f"Error: {e}")

        # Cleanup
        try:
            await executor.disconnect()
            record_result(broker, "disconnect", True, "Disconnected cleanly")
        except Exception as e:
            record_result(broker, "disconnect", False, f"Error: {e}")

    except ImportError as e:
        record_result(broker, "import", False, f"Import error: {e}")
    except Exception as e:
        record_result(broker, "general", False, f"Unexpected error: {e}")


async def test_mt4(account: TradingAccount, credentials: Dict[str, Any]) -> None:
    """Test MT4 executor functions."""
    broker = "mt4"

    try:
        from app.brokers.mt4_executor import MT4Executor
        from app.core.config import settings

        # Check credentials
        metaapi_account_id = credentials.get("metaapi_account_id")
        metaapi_token = credentials.get("metaapi_token") or credentials.get("api_token") or getattr(settings, 'METAAPI_TOKEN', None)

        if not metaapi_account_id:
            record_result(broker, "credentials_check", False, "Missing metaapi_account_id")
            return
        if not metaapi_token:
            record_result(broker, "credentials_check", False, "Missing metaapi_token")
            return

        record_result(broker, "credentials_check", True, f"Credentials available (account_id: {metaapi_account_id[:8]}...)")

        # Create executor
        executor = MT4Executor(
            metaapi_token=metaapi_token,
            metaapi_account_id=metaapi_account_id,
        )

        record_result(broker, "executor_create", True, "Executor created")

        # Initialize
        try:
            init_result = await asyncio.wait_for(executor.initialize(), timeout=60.0)
            if init_result:
                record_result(broker, "initialize", True, "Connected successfully")
            else:
                record_result(broker, "initialize", False, "Initialize returned False")
                return
        except asyncio.TimeoutError:
            record_result(broker, "initialize", False, "Connection timed out (60s)")
            return
        except Exception as e:
            record_result(broker, "initialize", False, f"Connection error: {e}")
            return

        # Test get_accounts
        try:
            accounts = await asyncio.wait_for(executor.get_accounts(), timeout=15.0)
            record_result(broker, "get_accounts", True, f"Found {len(accounts)} accounts",
                         [{"id": a.id, "balance": a.balance} for a in accounts[:3]])
        except Exception as e:
            record_result(broker, "get_accounts", False, f"Error: {e}")

        # Test get_positions
        try:
            positions = await asyncio.wait_for(executor.get_positions(), timeout=15.0)
            record_result(broker, "get_positions", True, f"Found {len(positions)} positions")
        except Exception as e:
            record_result(broker, "get_positions", False, f"Error: {e}")

        # Cleanup
        try:
            await executor.disconnect()
            record_result(broker, "disconnect", True, "Disconnected cleanly")
        except Exception as e:
            record_result(broker, "disconnect", False, f"Error: {e}")

    except ImportError as e:
        record_result(broker, "import", False, f"Import error: {e}")
    except Exception as e:
        record_result(broker, "general", False, f"Unexpected error: {e}")


async def run_all_tests():
    """Run tests for all active trading accounts."""
    print("\n" + "="*60)
    print("🧪 TRADING FUNCTIONS TEST SUITE")
    print("="*60 + "\n")

    db = SessionLocal()

    try:
        # Get all active trading accounts
        accounts = db.query(TradingAccount).filter(
            TradingAccount.is_active == True
        ).all()

        if not accounts:
            print("❌ No active trading accounts found in database")
            return

        print(f"📋 Found {len(accounts)} active trading accounts\n")

        # Group accounts by broker
        broker_accounts: Dict[str, List[TradingAccount]] = {}
        for account in accounts:
            broker = account.broker.value
            if broker not in broker_accounts:
                broker_accounts[broker] = []
            broker_accounts[broker].append(account)

        # Test each broker (use first account of each type)
        for broker, accts in broker_accounts.items():
            account = accts[0]  # Test with first account
            print(f"\n{'='*50}")
            print(f"🔧 Testing {broker.upper()} (Account: {account.account_name or account.account_number})")
            print(f"{'='*50}")

            credentials = load_credentials(db, account)

            if broker == "tradelocker":
                await test_tradelocker(account, credentials)
            elif broker == "mt5":
                await test_mt5(account, credentials)
            elif broker == "mt4":
                await test_mt4(account, credentials)
            elif broker in ("projectx", "topstep"):
                await test_projectx(account, credentials)
            elif broker == "tradovate":
                await test_tradovate(account, credentials)
            else:
                record_result(broker, "unsupported", False, f"No test handler for broker: {broker}")

        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)

        total_passed = 0
        total_failed = 0

        for broker, results in test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed
            total_passed += passed
            total_failed += failed

            status = "✅" if failed == 0 else "⚠️" if passed > 0 else "❌"
            print(f"\n{status} {broker.upper()}: {passed}/{total} tests passed")

            for test in results["tests"]:
                icon = "✓" if test["success"] else "✗"
                print(f"   {icon} {test['test']}: {test['message']}")

        print(f"\n{'='*60}")
        print(f"TOTAL: {total_passed} passed, {total_failed} failed")
        print("="*60 + "\n")

        return total_failed == 0

    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
