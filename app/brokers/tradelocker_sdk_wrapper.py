"""
TradeLocker SDK Async Wrapper

Provides async interface around the synchronous official TradeLocker SDK.
Uses ThreadPoolExecutor to avoid blocking the async event loop.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List
from functools import partial

logger = logging.getLogger(__name__)


class TradeLockerSDKWrapper:
    """
    Async wrapper for the synchronous TradeLocker SDK (TLAPI).

    The official tradelocker package is synchronous and uses requests.
    This wrapper uses ThreadPoolExecutor to run SDK calls without blocking
    the async event loop.

    Usage:
        wrapper = TradeLockerSDKWrapper(
            environment="https://demo.tradelocker.com",
            username="user@email.com",
            password="password",
            server="Demo Server"
        )
        await wrapper.initialize()
        instruments = await wrapper.get_all_instruments()
    """

    def __init__(
        self,
        environment: str,
        username: str,
        password: str,
        server: str,
        max_workers: int = 3,
        account_id: Optional[int] = None,
        account_num: Optional[int] = None,
    ):
        """
        Initialize the SDK wrapper.

        Args:
            environment: SDK environment URL (e.g., "https://demo.tradelocker.com")
            username: TradeLocker account username (email)
            password: TradeLocker account password
            server: TradeLocker server name
            max_workers: Max concurrent threads for SDK calls
            account_id: Pre-resolved account ID (skip discovery if provided)
            account_num: Pre-resolved account number (skip discovery if provided)
        """
        self._environment = environment
        self._username = username
        self._password = password
        self._server = server
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tl = None
        self._initialized = False
        # Pre-resolved account info (avoids rediscovery on each init)
        self._acc_num = account_num
        self._acc_id = account_id

    async def initialize(self) -> bool:
        """
        Initialize the SDK connection.

        This authenticates with TradeLocker and retrieves account info.
        Returns True if successful, False otherwise.
        """
        try:
            # Import here to avoid import errors if SDK not installed
            from tradelocker import TLAPI

            loop = asyncio.get_event_loop()

            # Create TLAPI instance in thread pool (it authenticates on construction)
            def create_client():
                return TLAPI(
                    environment=self._environment,
                    username=self._username,
                    password=self._password,
                    server=self._server
                )

            self._tl = await loop.run_in_executor(self._executor, create_client)

            # If account_id/account_num were pre-resolved (from stored credentials), skip discovery
            if self._acc_id is not None and self._acc_num is not None:
                logger.info(f"Using pre-resolved account: num={self._acc_num}, id={self._acc_id}")
            else:
                # Get default account from get_all_accounts() (v0.56.1+ compatible)
                # get_acc_nums/get_acc_ids don't exist in newer SDK versions
                def get_first_account():
                    try:
                        accounts = self._tl.get_all_accounts()
                        if accounts is not None and len(accounts) > 0:
                            # accounts is a DataFrame with columns: id, accNum, etc.
                            first_row = accounts.iloc[0]
                            acc_id = first_row.get('id', first_row.get('accountId', None))
                            acc_num = first_row.get('accNum', first_row.get('accountNumber', acc_id))
                            return acc_num, acc_id
                    except Exception as e:
                        logger.warning(f"Failed to get accounts via get_all_accounts: {e}")
                    return None, None

                self._acc_num, self._acc_id = await loop.run_in_executor(self._executor, get_first_account)

            self._initialized = True
            logger.info(f"TradeLocker SDK initialized. Account: {self._acc_num}, ID: {self._acc_id}")
            return True

        except ImportError:
            logger.error("TradeLocker SDK not installed. Run: pip install tradelocker")
            return False
        except Exception as e:
            logger.error(f"TradeLocker SDK initialization failed: {e}")
            return False

    @property
    def is_initialized(self) -> bool:
        """Check if SDK is initialized and ready."""
        return self._initialized and self._tl is not None

    @property
    def account_number(self) -> Optional[int]:
        """Get the default account number."""
        return self._acc_num

    @property
    def account_id(self) -> Optional[int]:
        """Get the default account ID."""
        return self._acc_id

    def _run_sync(self, func, *args, **kwargs):
        """Helper to run sync function in executor."""
        if kwargs:
            return partial(func, *args, **kwargs)
        if args:
            return partial(func, *args)
        return func

    async def get_all_broker_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all broker accounts under this login.

        Returns list of account dicts with:
        - broker_account_id: unique account ID
        - account_number: display account number
        - display_name: account name
        - status: 'active', 'inactive', 'blown', 'expired'
        - account_type: 'DEMO' or 'LIVE'
        - balance: account balance
        - equity: account equity
        - currency: account currency
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return []

        try:
            loop = asyncio.get_event_loop()

            def fetch_all_accounts():
                accounts_df = self._tl.get_all_accounts()
                if accounts_df is None or len(accounts_df) == 0:
                    return []

                result = []
                for _, row in accounts_df.iterrows():
                    acc_id = row.get('id', row.get('accountId', ''))
                    acc_num = row.get('accNum', row.get('accountNumber', acc_id))
                    name = row.get('name', f'Account {acc_num}')
                    balance = float(row.get('accountBalance', row.get('balance', 0)))
                    status_raw = str(row.get('status', 'ACTIVE')).upper()

                    # Determine status
                    if status_raw == 'ACTIVE':
                        # Check if account is "blown" (balance below threshold)
                        if balance < 100:
                            status = 'blown'
                        else:
                            status = 'active'
                    elif status_raw in ('INACTIVE', 'DISABLED'):
                        status = 'inactive'
                    elif status_raw in ('EXPIRED', 'CLOSED'):
                        status = 'expired'
                    else:
                        status = 'active'

                    result.append({
                        'broker_account_id': str(acc_id),
                        'account_number': str(acc_num),
                        'display_name': name,
                        'status': status,
                        'account_type': 'DEMO',  # TradeLocker demo
                        'balance': balance,
                        'equity': balance,  # Same as balance if not provided
                        'currency': row.get('currency', 'USD'),
                        'meta': {
                            'balance': balance,
                            'equity': balance,
                            'currency': row.get('currency', 'USD'),
                        }
                    })
                return result

            return await loop.run_in_executor(self._executor, fetch_all_accounts)
        except Exception as e:
            logger.error(f"Failed to get all broker accounts: {e}")
            return []

    async def get_all_instruments(self) -> Optional[Any]:
        """
        Get all available instruments.

        Returns DataFrame with instrument info or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                self._tl.get_all_instruments
            )
        except Exception as e:
            logger.error(f"Failed to get instruments: {e}")
            return None

    async def get_price_history(
        self,
        instrument_id: int,
        resolution: str = "1D",
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        lookback_period: str = "5D"
    ) -> Optional[Any]:
        """
        Get price history for an instrument.

        Args:
            instrument_id: Instrument ID to fetch
            resolution: Time resolution (1m, 5m, 15m, 1H, 4H, 1D, etc.)
            start_timestamp: Start timestamp in milliseconds
            end_timestamp: End timestamp in milliseconds
            lookback_period: Alternative to timestamps (5D, 1M, etc.)

        Returns DataFrame with OHLCV data or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                lambda: self._tl.get_price_history(
                    instrument_id=instrument_id,
                    resolution=resolution,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    lookback_period=lookback_period
                )
            )
        except Exception as e:
            logger.error(f"Failed to get price history: {e}")
            return None

    async def get_latest_asking_price(self, instrument_id: int) -> Optional[float]:
        """
        Get latest asking price for an instrument.

        Args:
            instrument_id: Instrument ID

        Returns ask price or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                lambda: self._tl.get_latest_asking_price(instrument_id)
            )
        except Exception as e:
            logger.error(f"Failed to get asking price: {e}")
            return None

    async def create_order(
        self,
        instrument_id: int,
        quantity: float,
        side: str,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss_type: str = "absolute",
        take_profit_type: str = "absolute",
        validity: str = "GTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new order.

        Args:
            instrument_id: Instrument ID to trade
            quantity: Order quantity (lots)
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop'
            price: Limit/stop price (required for limit/stop orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            stop_loss_type: 'absolute' or 'offset'
            take_profit_type: 'absolute' or 'offset'
            validity: Order validity (GTC, DAY, IOC, FOK)

        Returns order result dict or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()

            # The SDK uses 'type_' parameter for order type
            result = await loop.run_in_executor(
                self._executor,
                lambda: self._tl.create_order(
                    instrument_id=instrument_id,
                    quantity=quantity,
                    side=side,
                    type_=order_type,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    stop_loss_type=stop_loss_type,
                    take_profit_type=take_profit_type,
                    validity=validity
                )
            )

            logger.info(f"Order created: {result}")
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return {"success": False, "error": str(e)}

    async def close_position(
        self,
        position_id: int,
        quantity: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Close a position.

        Args:
            position_id: Position ID to close
            quantity: Quantity to close (None = full close)

        Returns close result dict or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()

            # SDK close_position takes position_id and optionally quantity
            if quantity:
                result = await loop.run_in_executor(
                    self._executor,
                    lambda: self._tl.close_position(position_id, quantity)
                )
            else:
                result = await loop.run_in_executor(
                    self._executor,
                    lambda: self._tl.close_position(position_id)
                )

            logger.info(f"Position close result: {result}")

            # SDK returns False if position not found, True or orderId on success
            if result is False:
                return {"success": False, "error": "Position not found or already closed"}
            elif result is True or isinstance(result, (int, str)):
                return {"success": True, "result": {"id": str(result) if result is not True else position_id}}
            elif isinstance(result, dict):
                return {"success": True, "result": result}
            else:
                return {"success": True, "result": {"id": str(position_id)}}

        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return {"success": False, "error": str(e)}

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.

        Returns list of position dicts.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return []

        try:
            loop = asyncio.get_event_loop()

            # The SDK returns positions through account state
            # We need to use get_all_positions or similar
            result = await loop.run_in_executor(
                self._executor,
                lambda: self._tl.get_all_positions()
            )

            # Convert to list of dicts if DataFrame
            if hasattr(result, 'to_dict'):
                return result.to_dict('records')
            return result if result else []

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    async def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all pending orders.

        Returns list of order dicts.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return []

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self._executor,
                lambda: self._tl.get_all_orders()
            )

            # Convert to list of dicts if DataFrame
            if hasattr(result, 'to_dict'):
                return result.to_dict('records')
            return result if result else []

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    async def modify_order(
        self,
        order_id: int,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Modify an existing order.

        Args:
            order_id: Order ID to modify
            price: New price (for limit/stop orders)
            stop_loss: New stop loss
            take_profit: New take profit

        Returns modification result or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self._executor,
                lambda: self._tl.modify_order(
                    order_id=order_id,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            )

            logger.info(f"Order modified: {result}")
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Failed to modify order: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Cancel a pending order.

        Args:
            order_id: Order ID to cancel

        Returns cancellation result or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self._executor,
                lambda: self._tl.delete_order(order_id)
            )

            logger.info(f"Order cancelled: {result}")
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {"success": False, "error": str(e)}

    async def get_account_state(self) -> Optional[Dict[str, Any]]:
        """
        Get current account state including balance, equity, margin.

        Returns account state dict or None on error.
        """
        if not self.is_initialized:
            logger.error("SDK not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self._executor,
                lambda: self._tl.get_account_state()
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get account state: {e}")
            return None

    async def get_instrument_id_by_symbol(self, symbol: str) -> Optional[int]:
        """
        Look up instrument ID by symbol name.

        Args:
            symbol: Symbol name (e.g., "EURUSD", "BTCUSD")

        Returns instrument ID or None if not found.
        """
        instruments = await self.get_all_instruments()
        if instruments is None:
            return None

        try:
            # Filter by symbol name
            if hasattr(instruments, 'loc'):
                # DataFrame
                matches = instruments[instruments['name'] == symbol]
                if not matches.empty:
                    return int(matches.iloc[0]['tradableInstrumentId'])
            else:
                # List of dicts
                for inst in instruments:
                    if inst.get('name') == symbol:
                        return inst.get('tradableInstrumentId')

            logger.warning(f"Instrument not found: {symbol}")
            return None

        except Exception as e:
            logger.error(f"Failed to lookup instrument: {e}")
            return None

    def shutdown(self):
        """Shutdown the thread pool executor."""
        self._executor.shutdown(wait=True)
        self._initialized = False
        logger.info("TradeLocker SDK wrapper shut down")
