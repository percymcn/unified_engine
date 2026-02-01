#!/usr/bin/env python3
"""
TradeLocker Trading Functions Test Suite

Tests all TradeLocker trading functions directly using stored credentials from the database.
This script verifies:
1. Market Buy/Sell
2. Limit Buy/Sell
3. Stop Buy/Sell
4. Close Position
5. Close All Positions
6. Modify Position (SL/TP)
7. Trailing Stop (via stop_loss_type='trailingOffset')

Usage:
    python scripts/test_tradelocker_all_functions.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class TestResult:
    """Simple test result tracker"""
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.message = ""
        self.data: Dict[str, Any] = {}
        self.duration_ms = 0

    def __str__(self):
        status = "✅ PASS" if self.success else "❌ FAIL"
        return f"{status} | {self.name}: {self.message}"


async def get_tradelocker_credentials():
    """Get TradeLocker credentials from database"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://trading_user:trading_password@localhost:5432/trading_db"
    )

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        from app.models.database_models import TradingAccount, BrokerType, Credential
        from app.core.encryption import decrypt_dict

        # Get first TradeLocker account
        account = session.query(TradingAccount).filter(
            TradingAccount.broker == BrokerType.TRADELOCKER,
            TradingAccount.is_active == True
        ).first()

        if not account:
            logger.error("No active TradeLocker account found")
            return None

        # Get credentials from Credential table
        credential = session.query(Credential).filter(
            Credential.user_id == account.user_id,
            Credential.service == "tradelocker",
            Credential.is_active == True
        ).first()

        if not credential:
            logger.error("No TradeLocker credentials found")
            return None

        # Decrypt credentials
        try:
            creds = decrypt_dict(credential.encrypted_data)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            return None

        # Get broker_account_id from extra_metadata or default_broker_account_id
        broker_account_id = account.default_broker_account_id
        if not broker_account_id and account.extra_metadata:
            broker_account_id = account.extra_metadata.get("broker_account_id")

        return {
            "username": creds.get("username") or creds.get("email"),
            "password": creds.get("password"),
            "server": creds.get("server"),
            "environment": creds.get("environment", "https://demo.tradelocker.com"),
            "account_id": broker_account_id,
            "account_num": account.account_number,
            "db_account_id": account.id,
        }
    finally:
        session.close()


async def run_test_suite():
    """Run the complete TradeLocker test suite"""
    print("\n" + "="*70)
    print("🧪 TRADELOCKER TRADING FUNCTIONS TEST SUITE")
    print("="*70 + "\n")

    results = []

    # Get credentials
    print("📋 Loading TradeLocker credentials from database...")
    creds = await get_tradelocker_credentials()
    if not creds:
        print("❌ Failed to load credentials. Ensure a TradeLocker account exists.")
        return

    print(f"   Account: {creds['account_num']}")
    print(f"   Server: {creds['server']}")
    print(f"   Environment: {creds['environment']}\n")

    # Initialize SDK wrapper
    from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

    # Parse account IDs (may be int or UUID string)
    account_id = creds.get("account_id")
    account_num = creds.get("account_num")

    # Try to convert to int if numeric
    try:
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
    except (ValueError, TypeError):
        account_id = None

    try:
        account_num = int(account_num) if account_num and str(account_num).isdigit() else None
    except (ValueError, TypeError):
        account_num = None

    wrapper = TradeLockerSDKWrapper(
        environment=creds["environment"],
        username=creds["username"],
        password=creds["password"],
        server=creds["server"],
        account_id=account_id,
        account_num=account_num,
    )

    # Initialize connection
    print("🔌 Initializing TradeLocker connection...")
    init_result = TestResult("SDK Initialization")
    start = datetime.now()
    try:
        success = await wrapper.initialize()
        init_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        init_result.success = success
        init_result.message = f"Connected in {init_result.duration_ms}ms" if success else "Failed to connect"
    except Exception as e:
        init_result.message = str(e)
    results.append(init_result)
    print(f"   {init_result}\n")

    if not init_result.success:
        print("❌ Cannot continue without SDK connection")
        return results

    # Get account state
    print("💰 Fetching account state...")
    account_result = TestResult("Get Account State")
    start = datetime.now()
    try:
        state = await wrapper.get_account_state()
        account_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        if state:
            account_result.success = True
            account_result.data = state
            balance = state.get("balance", 0)
            equity = state.get("equity", 0)
            account_result.message = f"Balance: ${balance:,.2f}, Equity: ${equity:,.2f}"
        else:
            account_result.message = "No account state returned"
    except Exception as e:
        account_result.message = str(e)
    results.append(account_result)
    print(f"   {account_result}\n")

    # Get instrument ID for testing
    TEST_SYMBOL = "BTCUSD"  # Available 24/7
    print(f"🔍 Looking up instrument: {TEST_SYMBOL}...")
    instrument_id = await wrapper.get_instrument_id_by_symbol(TEST_SYMBOL)
    if not instrument_id:
        print(f"❌ Instrument {TEST_SYMBOL} not found. Trying EURUSD...")
        TEST_SYMBOL = "EURUSD"
        instrument_id = await wrapper.get_instrument_id_by_symbol(TEST_SYMBOL)

    if not instrument_id:
        print("❌ No valid instrument found for testing")
        return results

    print(f"   Found instrument ID: {instrument_id}\n")

    # Get current price
    print(f"📊 Getting current price for {TEST_SYMBOL}...")
    price = await wrapper.get_latest_asking_price(instrument_id)
    print(f"   Current price: {price}\n")

    # ============================================
    # TEST 1: Market Buy
    # ============================================
    print("="*50)
    print("TEST 1: MARKET BUY")
    print("="*50)
    test_qty = 0.01
    market_buy_result = TestResult("Market Buy")
    start = datetime.now()
    try:
        result = await wrapper.create_order(
            instrument_id=instrument_id,
            quantity=test_qty,
            side="buy",
            order_type="market",
            validity="IOC"
        )
        market_buy_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        market_buy_result.data = result
        if result and result.get("success"):
            market_buy_result.success = True
            market_buy_result.message = f"Order placed: {result.get('result')}"
        else:
            market_buy_result.message = result.get("error") if result else "No response"
    except Exception as e:
        market_buy_result.message = str(e)
    results.append(market_buy_result)
    print(f"   {market_buy_result}\n")

    # Wait for order to fill
    await asyncio.sleep(2)

    # Get positions to find the one we just opened
    positions = await wrapper.get_positions()
    print(f"   Current positions: {len(positions)}")

    position_id = None
    for pos in positions:
        if isinstance(pos, dict):
            inst_id = pos.get("tradableInstrumentId")
            if inst_id == instrument_id:
                position_id = pos.get("id")
                print(f"   Found position ID: {position_id}")
                break

    # ============================================
    # TEST 2: Modify Position (Add SL/TP)
    # ============================================
    if position_id:
        print("\n" + "="*50)
        print("TEST 2: MODIFY POSITION (SL/TP)")
        print("="*50)
        modify_result = TestResult("Modify Position SL/TP")
        start = datetime.now()
        try:
            # Set SL 100 pips below, TP 100 pips above current price
            sl_price = price - 100 if price else None
            tp_price = price + 100 if price else None

            result = await wrapper.modify_position(
                position_id=int(position_id),
                stop_loss=sl_price,
                take_profit=tp_price,
                stop_loss_type="absolute",
                take_profit_type="absolute"
            )
            modify_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            modify_result.data = result
            if result and result.get("success"):
                modify_result.success = True
                modify_result.message = f"Position modified: SL={sl_price}, TP={tp_price}"
            else:
                modify_result.message = result.get("error") if result else "No response"
        except Exception as e:
            modify_result.message = str(e)
        results.append(modify_result)
        print(f"   {modify_result}\n")

        await asyncio.sleep(1)

        # ============================================
        # TEST 3: Modify with Trailing Stop
        # ============================================
        print("="*50)
        print("TEST 3: TRAILING STOP")
        print("="*50)
        trailing_result = TestResult("Trailing Stop")
        start = datetime.now()
        try:
            # Set trailing stop at 50 pips
            result = await wrapper.modify_position(
                position_id=int(position_id),
                stop_loss=50,  # 50 pip trailing distance
                stop_loss_type="trailingOffset"
            )
            trailing_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            trailing_result.data = result
            if result and result.get("success"):
                trailing_result.success = True
                trailing_result.message = "Trailing stop set at 50 pips"
            else:
                trailing_result.message = result.get("error") if result else "No response"
        except Exception as e:
            trailing_result.message = str(e)
        results.append(trailing_result)
        print(f"   {trailing_result}\n")

        await asyncio.sleep(1)

        # ============================================
        # TEST 4: Close Position
        # ============================================
        print("="*50)
        print("TEST 4: CLOSE POSITION")
        print("="*50)
        close_result = TestResult("Close Position")
        start = datetime.now()
        try:
            result = await wrapper.close_position(position_id=int(position_id))
            close_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            close_result.data = result
            if result and result.get("success"):
                close_result.success = True
                close_result.message = f"Position {position_id} closed"
            else:
                close_result.message = result.get("error") if result else "No response"
        except Exception as e:
            close_result.message = str(e)
        results.append(close_result)
        print(f"   {close_result}\n")

    await asyncio.sleep(1)

    # ============================================
    # TEST 5: Market Sell
    # ============================================
    print("="*50)
    print("TEST 5: MARKET SELL")
    print("="*50)
    market_sell_result = TestResult("Market Sell")
    start = datetime.now()
    try:
        result = await wrapper.create_order(
            instrument_id=instrument_id,
            quantity=test_qty,
            side="sell",
            order_type="market",
            validity="IOC"
        )
        market_sell_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        market_sell_result.data = result
        if result and result.get("success"):
            market_sell_result.success = True
            market_sell_result.message = f"Order placed: {result.get('result')}"
        else:
            market_sell_result.message = result.get("error") if result else "No response"
    except Exception as e:
        market_sell_result.message = str(e)
    results.append(market_sell_result)
    print(f"   {market_sell_result}\n")

    await asyncio.sleep(2)

    # ============================================
    # TEST 6: Close All Positions
    # ============================================
    print("="*50)
    print("TEST 6: CLOSE ALL POSITIONS")
    print("="*50)
    close_all_result = TestResult("Close All Positions")
    start = datetime.now()
    try:
        result = await wrapper.close_all_positions()
        close_all_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        close_all_result.data = result
        if result and result.get("success"):
            close_all_result.success = True
            close_all_result.message = f"All positions closed: {result.get('result')}"
        else:
            close_all_result.message = result.get("error") if result else "No response"
    except Exception as e:
        close_all_result.message = str(e)
    results.append(close_all_result)
    print(f"   {close_all_result}\n")

    await asyncio.sleep(1)

    # ============================================
    # TEST 7: Limit Buy Order
    # ============================================
    print("="*50)
    print("TEST 7: LIMIT BUY ORDER")
    print("="*50)
    limit_price = price - 50 if price else 90000  # 50 below current
    limit_buy_result = TestResult("Limit Buy")
    start = datetime.now()
    try:
        result = await wrapper.create_order(
            instrument_id=instrument_id,
            quantity=test_qty,
            side="buy",
            order_type="limit",
            price=limit_price,
            validity="GTC"
        )
        limit_buy_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        limit_buy_result.data = result
        if result and result.get("success"):
            limit_buy_result.success = True
            limit_buy_result.message = f"Limit order placed at {limit_price}: {result.get('result')}"
        else:
            limit_buy_result.message = result.get("error") if result else "No response"
    except Exception as e:
        limit_buy_result.message = str(e)
    results.append(limit_buy_result)
    print(f"   {limit_buy_result}\n")

    await asyncio.sleep(1)

    # Get pending orders to find order ID
    orders = await wrapper.get_orders()
    print(f"   Pending orders: {len(orders)}")

    order_id = None
    for order in orders:
        if isinstance(order, dict):
            order_id = order.get("id")
            if order_id:
                print(f"   Found order ID: {order_id}")
                break

    # ============================================
    # TEST 8: Cancel Order
    # ============================================
    if order_id:
        print("\n" + "="*50)
        print("TEST 8: CANCEL ORDER")
        print("="*50)
        cancel_result = TestResult("Cancel Order")
        start = datetime.now()
        try:
            result = await wrapper.cancel_order(int(order_id))
            cancel_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            cancel_result.data = result
            if result and result.get("success"):
                cancel_result.success = True
                cancel_result.message = f"Order {order_id} cancelled"
            else:
                cancel_result.message = result.get("error") if result else "No response"
        except Exception as e:
            cancel_result.message = str(e)
        results.append(cancel_result)
        print(f"   {cancel_result}\n")

    await asyncio.sleep(1)

    # ============================================
    # TEST 9: Stop Buy Order
    # ============================================
    print("="*50)
    print("TEST 9: STOP BUY ORDER")
    print("="*50)
    stop_price = price + 50 if price else 100000  # 50 above current
    stop_buy_result = TestResult("Stop Buy")
    start = datetime.now()
    try:
        result = await wrapper.create_order(
            instrument_id=instrument_id,
            quantity=test_qty,
            side="buy",
            order_type="stop",
            price=stop_price,
            validity="GTC"
        )
        stop_buy_result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        stop_buy_result.data = result
        if result and result.get("success"):
            stop_buy_result.success = True
            stop_buy_result.message = f"Stop order placed at {stop_price}: {result.get('result')}"
        else:
            stop_buy_result.message = result.get("error") if result else "No response"
    except Exception as e:
        stop_buy_result.message = str(e)
    results.append(stop_buy_result)
    print(f"   {stop_buy_result}\n")

    await asyncio.sleep(1)

    # Cancel any remaining orders
    print("🧹 Cleaning up pending orders...")
    orders = await wrapper.get_orders()
    for order in orders:
        if isinstance(order, dict) and order.get("id"):
            try:
                await wrapper.cancel_order(int(order["id"]))
                print(f"   Cancelled order {order['id']}")
            except:
                pass

    # Shutdown
    wrapper.shutdown()

    # ============================================
    # SUMMARY
    # ============================================
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed

    for r in results:
        print(f"   {r}")

    print("\n" + "-"*70)
    print(f"   Total: {len(results)} | Passed: {passed} ✅ | Failed: {failed} ❌")
    print("="*70 + "\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_test_suite())
