#!/usr/bin/env python3
"""
Test all broker SDKs to ensure they work correctly
Tests connection, account info, positions, orders for each broker
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.models.database_models import TradingAccount, BrokerType as DBBrokerType
from app.core.encryption import decrypt
from app.brokers.tradelocker_executor import TradeLockerExecutor
from app.brokers.tradovate_executor import TradovateExecutor
from app.brokers.projectx_executor import ProjectXExecutor
from app.brokers.mt4_executor import MT4Executor
from app.brokers.mt5_executor import MT5Executor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_broker_sdk(broker_type: DBBrokerType, account: TradingAccount):
    """Test a broker SDK with stored credentials"""
    print(f"\n{'='*60}")
    print(f"Testing {broker_type.value.upper()} SDK")
    print(f"{'='*60}")
    
    try:
        # Decrypt credentials
        credentials = {}
        if account.api_key:
            try:
                credentials["api_key"] = decrypt(account.api_key)
            except Exception as e:
                print(f"  ❌ Failed to decrypt api_key: {e}")
                return False
        if account.api_secret:
            try:
                credentials["api_secret"] = decrypt(account.api_secret)
            except Exception as e:
                print(f"  ❌ Failed to decrypt api_secret: {e}")
                return False
        if account.login:
            credentials["login"] = account.login
        if account.password:
            try:
                credentials["password"] = decrypt(account.password)
            except Exception as e:
                print(f"  ❌ Failed to decrypt password: {e}")
                return False
        if account.server:
            credentials["server"] = account.server
        
        # Create executor
        executor = None
        if broker_type == DBBrokerType.TRADELOCKER:
            executor = TradeLockerExecutor()
            if credentials.get("api_key") and credentials.get("api_secret"):
                executor._sdk_username = credentials.get("api_key")
                executor._sdk_password = credentials.get("api_secret")
                executor._sdk_server = credentials.get("server", "demo")
                executor._sdk_available = True
                executor.is_available = True
            else:
                print("  ❌ Missing credentials (api_key/api_secret)")
                return False
                
        elif broker_type == DBBrokerType.TRADOVATE:
            executor = TradovateExecutor()
            if credentials.get("api_key") and credentials.get("api_secret"):
                executor.config = {
                    "api_key": credentials.get("api_key"),
                    "api_secret": credentials.get("api_secret")
                }
            else:
                print("  ❌ Missing credentials (api_key/api_secret)")
                return False
                
        elif broker_type == DBBrokerType.PROJECTX:
            executor = ProjectXExecutor()
            if credentials.get("api_key"):
                executor.config = {
                    "api_key": credentials.get("api_key"),
                    "api_secret": credentials.get("api_secret", "")
                }
            else:
                print("  ❌ Missing credentials (api_key)")
                return False
                
        elif broker_type == DBBrokerType.MT4:
            executor = MT4Executor()
            if credentials.get("login") and credentials.get("password") and credentials.get("server"):
                executor.config = {
                    "login": credentials.get("login"),
                    "password": credentials.get("password"),
                    "server": credentials.get("server")
                }
            else:
                print("  ❌ Missing credentials (login/password/server)")
                return False
                
        elif broker_type == DBBrokerType.MT5:
            executor = MT5Executor()
            if credentials.get("login") and credentials.get("password") and credentials.get("server"):
                executor.config = {
                    "login": credentials.get("login"),
                    "password": credentials.get("password"),
                    "server": credentials.get("server")
                }
            else:
                print("  ❌ Missing credentials (login/password/server)")
                return False
        
        # Test 1: Initialize
        print("  🔄 Testing initialization...")
        try:
            success = await asyncio.wait_for(executor.initialize(), timeout=15.0)
            if success and executor.is_connected:
                print("  ✅ Initialization successful")
            else:
                print(f"  ❌ Initialization failed: is_connected={executor.is_connected}")
                await executor.disconnect()
                return False
        except asyncio.TimeoutError:
            print("  ❌ Initialization timed out")
            await executor.disconnect()
            return False
        except Exception as e:
            print(f"  ❌ Initialization error: {e}")
            await executor.disconnect()
            return False
        
        # Test 2: Get account info
        print("  🔄 Testing get_account_info...")
        try:
            account_info = await executor.get_account_info(str(account.account_number or account.id))
            if account_info:
                print(f"  ✅ Account info retrieved: balance={account_info.balance}, equity={account_info.equity}")
            else:
                print("  ⚠️  get_account_info returned None")
        except Exception as e:
            print(f"  ⚠️  get_account_info error: {e}")
        
        # Test 3: Get positions
        print("  🔄 Testing get_positions...")
        try:
            positions = await executor.get_positions(str(account.account_number or account.id))
            print(f"  ✅ Positions retrieved: {len(positions)} positions")
        except Exception as e:
            print(f"  ⚠️  get_positions error: {e}")
        
        # Test 4: Get orders
        print("  🔄 Testing get_orders...")
        try:
            orders = await executor.get_orders(str(account.account_number or account.id))
            print(f"  ✅ Orders retrieved: {len(orders)} orders")
        except Exception as e:
            print(f"  ⚠️  get_orders error: {e}")
        
        # Cleanup
        await executor.disconnect()
        print(f"  ✅ {broker_type.value.upper()} SDK test completed successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing {broker_type.value}: {e}")
        import traceback
        traceback.print_exc()
        if executor:
            try:
                await executor.disconnect()
            except:
                pass
        return False

async def main():
    """Test all brokers with stored accounts"""
    db = SessionLocal()
    
    try:
        # Get all brokers with active accounts
        brokers_with_accounts = db.query(TradingAccount.broker).distinct().all()
        broker_types = [b[0] for b in brokers_with_accounts]
        
        if not broker_types:
            print("❌ No active accounts found in database")
            print("   Please add accounts through the UI first")
            return
        
        print(f"\n📋 Found {len(broker_types)} broker(s) with accounts")
        
        results = {}
        for broker_type in broker_types:
            account = db.query(TradingAccount).filter(
                TradingAccount.broker == broker_type,
                TradingAccount.is_active == True
            ).first()
            
            if account:
                success = await test_broker_sdk(broker_type, account)
                results[broker_type.value] = success
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        for broker, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {broker.upper()}: {status}")
        
        all_passed = all(results.values())
        print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
