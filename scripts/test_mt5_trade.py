#!/usr/bin/env python3
"""
Direct MT5 Trade Test
Tests placing a small trade via MetaAPI SDK to verify comment length fix.
"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
from dotenv import load_dotenv
load_dotenv('/home/pharma5/unified_engine/.env')

METAAPI_TOKEN = os.getenv('METAAPI_TOKEN')
METAAPI_ACCOUNT_ID = '3f8fafd7-3f45-4dd4-8eca-838c6431b181'  # Account 59


async def test_trade(symbol: str, action: str = 'buy'):
    """Test placing a trade with proper comment length."""
    print(f"\n{'='*60}")
    print(f"Testing {action.upper()} {symbol}")
    print('='*60)

    try:
        from metaapi_cloud_sdk import MetaApi

        # Initialize MetaAPI
        print("1. Initializing MetaAPI SDK...")
        api = MetaApi(METAAPI_TOKEN)

        # Get account
        print(f"2. Getting account {METAAPI_ACCOUNT_ID}...")
        account = await api.metatrader_account_api.get_account(METAAPI_ACCOUNT_ID)
        print(f"   Account state: {account.state}")

        # Deploy if needed
        if account.state != 'DEPLOYED':
            print("3. Deploying account...")
            await account.deploy()
            await account.wait_deployed()
            print(f"   Account deployed")
        else:
            print("3. Account already deployed")

        # Get connection
        print("4. Getting streaming connection...")
        connection = account.get_streaming_connection()
        await connection.connect()

        # Wait for connection
        print("5. Waiting for synchronization...")
        await connection.wait_synchronized()
        print("   Connected and synchronized!")

        # Get terminal state
        terminal = connection.terminal_state
        print(f"   Balance: {terminal.account_information.get('balance', 'N/A')}")
        print(f"   Equity: {terminal.account_information.get('equity', 'N/A')}")

        # Test comment - must be <= 26 chars
        test_comment = "Test"  # 4 chars - well under limit
        print(f"\n6. Placing {action} order for {symbol}...")
        print(f"   Comment: '{test_comment}' (len={len(test_comment)})")
        print(f"   Volume: 0.01")

        # Place order
        options = {
            'comment': test_comment,
        }

        if action == 'buy':
            result = await connection.create_market_buy_order(
                symbol=symbol,
                volume=0.01,
                options=options
            )
        else:
            result = await connection.create_market_sell_order(
                symbol=symbol,
                volume=0.01,
                options=options
            )

        print(f"\n7. Order Result:")
        print(f"   Success: {result.get('stringCode') == 'TRADE_RETCODE_DONE'}")
        print(f"   String Code: {result.get('stringCode')}")
        print(f"   Order ID: {result.get('orderId')}")
        print(f"   Position ID: {result.get('positionId')}")

        if result.get('stringCode') == 'TRADE_RETCODE_DONE':
            print(f"\n   ✓ Trade successful!")

            # Wait a moment then close
            print("\n8. Waiting 3 seconds before closing...")
            await asyncio.sleep(3)

            # Close position
            position_id = result.get('positionId')
            if position_id:
                print(f"9. Closing position {position_id}...")
                close_result = await connection.close_position(position_id)
                print(f"   Close result: {close_result.get('stringCode')}")
                if close_result.get('stringCode') == 'TRADE_RETCODE_DONE':
                    print(f"   ✓ Position closed successfully!")
                else:
                    print(f"   ✗ Close failed: {close_result}")
        else:
            print(f"\n   ✗ Trade failed!")
            print(f"   Error: {result}")

        # Disconnect
        print("\n10. Disconnecting...")
        await connection.close()

        return result.get('stringCode') == 'TRADE_RETCODE_DONE'

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run trade tests."""
    print("="*60)
    print("MT5 DIRECT TRADE TEST")
    print("="*60)
    print(f"MetaAPI Account: {METAAPI_ACCOUNT_ID}")
    print(f"Token: {METAAPI_TOKEN[:20]}...")

    # Test BTCUSD
    btc_success = await test_trade('BTCUSD', 'buy')

    # Small delay between trades
    await asyncio.sleep(2)

    # Test ETHUSD
    eth_success = await test_trade('ETHUSD', 'buy')

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"  BTCUSD: {'✓ PASS' if btc_success else '✗ FAIL'}")
    print(f"  ETHUSD: {'✓ PASS' if eth_success else '✗ FAIL'}")

    return 0 if (btc_success and eth_success) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
