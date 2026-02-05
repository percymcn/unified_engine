"""
ProjectX SDK Service
Wraps official project-x-py SDK for use in Tradeflow.

Uses the official project-x-py SDK for TopStep/ProjectX Gateway API integration.
Provides async-first interface matching existing executor patterns.

Comprehensive SDK Features:
- TradingSuite: Multi-instrument trading environment
- OrderManager: Advanced order management (bracket orders, order chains, stop loss/take profit)
- PositionManager: Position analytics, portfolio metrics, risk management
- OrderBook: Level 2 market depth analysis
- RealtimeDataManager: Real-time data streaming
- ProjectXRealtimeClient: WebSocket real-time connections
- Statistics: Session statistics and analytics
- Technical Indicators: RSI, MACD, Bollinger Bands, etc.
- Risk Management: Position sizing, risk analysis
- Portfolio Analytics: Cross-instrument analysis
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.contract_resolver import ContractResolver, get_contract_resolver

def normalize_symbol(symbol: str) -> str:
    """Normalize TradingView symbols to ProjectX base symbols."""
    return ContractResolver.normalize_symbol(symbol)

logger = logging.getLogger(__name__)

# Try to import SDK - graceful fallback if not installed
try:
    from project_x_py import (
        ProjectX, TradingSuite, OrderManager, PositionManager, OrderBook,
        RealtimeDataManager, ProjectXRealtimeClient
    )
    # Import technical indicators
    from project_x_py import (
        calculate_rsi, calculate_macd, calculate_bollinger_bands,
        calculate_atr, calculate_ema, calculate_sma, calculate_stochastic,
        calculate_obv, calculate_vwap, calculate_adx, calculate_commodity_channel_index,
        calculate_williams_r, calculate_sharpe_ratio, calculate_max_drawdown
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ProjectX = None
    TradingSuite = None
    OrderManager = None
    PositionManager = None
    OrderBook = None
    RealtimeDataManager = None
    ProjectXRealtimeClient = None
    logger.warning("project-x-py SDK not installed, ProjectXSDKService unavailable")


class ProjectXSDKService:
    """
    Service wrapper for project-x-py SDK.

    Manages SDK lifecycle, authentication, and provides
    unified interface for trading operations.
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        account_name: Optional[str] = None
    ):
        """
        Initialize ProjectX SDK service.

        Args:
            username: TopStep username/email
            api_key: TopStep API key
            account_name: Optional account name to select
        """
        self.username = username
        self.api_key = api_key
        self.account_name = account_name
        self._client: Optional[Any] = None  # ProjectX client
        self._suite: Optional[Any] = None  # TradingSuite
        self._contract_resolver: ContractResolver = get_contract_resolver()
        self._is_connected = False

    async def connect(self) -> bool:
        """
        Initialize SDK connection and authenticate.

        Returns:
            True if connection successful, False otherwise
        """
        if not SDK_AVAILABLE:
            logger.error("project-x-py SDK not available")
            return False

        try:
            # Create client with credentials
            self._client = ProjectX(
                username=self.username,
                api_key=self.api_key,
                account_name=self.account_name
            )

            # Authenticate
            await self._client.authenticate()

            self._is_connected = True
            account_info = self._client.account_info
            account_display = getattr(account_info, 'name', 'Unknown') if account_info else 'Unknown'
            logger.info(f"ProjectX SDK connected: {account_display}")
            return True

        except Exception as e:
            logger.error(f"ProjectX SDK connection failed: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Close SDK connections."""
        if self._suite:
            try:
                await self._suite.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting suite: {e}")
            self._suite = None

        if self._client:
            # ProjectX client cleanup
            self._client = None

        self._is_connected = False
        logger.info("ProjectX SDK disconnected")

    @staticmethod
    async def discover_accounts_static(username: str, api_key: str) -> List[Dict[str, Any]]:
        """
        Discover all available accounts without requiring a pre-selected account.

        This is useful for the initial account discovery flow when we don't know
        which accounts exist yet. It handles the case where authentication fails
        because an invalid account name was provided, and parses the available
        accounts from the error message.

        Args:
            username: TopStep username/email
            api_key: TopStep API key

        Returns:
            List of account dicts with 'name' field containing SDK account names
            (e.g., 'PRAC-V2-95183-68790057')
        """
        if not SDK_AVAILABLE:
            logger.warning("SDK not available for discover_accounts_static")
            return []

        try:
            import re

            # Try to create client without account_name to trigger error with account list
            client = ProjectX(
                username=username,
                api_key=api_key,
                account_name=None  # Don't specify account
            )

            try:
                await client.authenticate()
                # If we get here, authentication succeeded (SDK picked first account)
                accounts = await client.list_accounts()
                result = []
                for acc in accounts:
                    name = getattr(acc, 'name', '')
                    acc_id = str(getattr(acc, 'id', ''))
                    balance = float(getattr(acc, 'balance', 0))
                    can_trade = getattr(acc, 'canTrade', True)

                    # Determine status
                    if not can_trade:
                        status = 'blown' if balance < 100 else 'inactive'
                    elif balance < 100:
                        status = 'blown'
                    else:
                        status = 'active'

                    result.append({
                        "id": acc_id,
                        "name": name,
                        "balance": balance,
                        "equity": balance,
                        "margin": 0.0,
                        "free_margin": balance,
                        "currency": "USD",
                        "status": status,
                        "can_trade": can_trade,
                        "is_live": not getattr(acc, 'simulated', True),
                    })
                logger.info(f"discover_accounts_static found {len(result)} accounts via SDK")
                return result

            except ValueError as e:
                # Parse account names from error message like:
                # "Account '...' not found. Available accounts: PRAC-V2-95183-68790057, 50KTC-V2-..."
                error_msg = str(e)
                if "Available accounts:" in error_msg:
                    match = re.search(r'Available accounts:\s*(.+)', error_msg)
                    if match:
                        account_names = [name.strip() for name in match.group(1).split(',')]
                        logger.info(f"discover_accounts_static parsed {len(account_names)} accounts from error: {account_names}")
                        return [
                            {
                                "id": "",  # Will be filled later
                                "name": name,
                                "balance": 0.0,
                                "equity": 0.0,
                                "margin": 0.0,
                                "free_margin": 0.0,
                                "currency": "USD",
                                "status": "active",
                                "can_trade": True,
                                "is_live": False,
                            }
                            for name in account_names
                        ]
                raise

        except Exception as e:
            logger.error(f"discover_accounts_static failed: {e}")
            return []

    @property
    def is_connected(self) -> bool:
        """Check if SDK is connected."""
        return self._is_connected and self._client is not None

    # =========================================================================
    # Contract Resolution (Auto-Rollover)
    # =========================================================================

    async def resolve_contract(self, base_symbol: str) -> Optional[str]:
        """
        Resolve a base symbol to its active contract ID.

        Handles automatic rollover - always returns the current front-month contract.

        Args:
            base_symbol: Base symbol like MNQ, ES, CL

        Returns:
            Active contract ID (e.g., CON.F.US.MNQ.H26) or None
        """
        if not self._client:
            raise RuntimeError("Not connected")

        # Initialize resolver if needed
        if not self._contract_resolver._initialized:
            await self._contract_resolver.initialize(self._client)

        contract = await self._contract_resolver.get_active_contract(base_symbol)
        return contract.contract_id if contract else None

    async def get_contract_info(self, base_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed contract info including tick size and value.

        Args:
            base_symbol: Base symbol

        Returns:
            Dict with contract details or None
        """
        if not self._client:
            raise RuntimeError("Not connected")

        if not self._contract_resolver._initialized:
            await self._contract_resolver.initialize(self._client)

        contract = await self._contract_resolver.get_active_contract(base_symbol)
        if not contract:
            return None

        return {
            "contract_id": contract.contract_id,
            "symbol": contract.symbol,
            "base_symbol": contract.base_symbol,
            "description": contract.description,
            "tick_size": contract.tick_size,
            "tick_value": contract.tick_value,
            "is_active": contract.is_active,
            "expiry_month": contract.expiry_month,
            "expiry_year": contract.expiry_year,
        }

    def get_all_tradeable_symbols(self) -> List[Dict[str, Any]]:
        """
        Get list of all tradeable symbols with their info.

        Returns:
            List of symbol info dicts
        """
        symbols = []
        for symbol, info in self._contract_resolver.TRADEABLE_SYMBOLS.items():
            symbols.append({
                "symbol": symbol,
                "name": info['name'],
                "tick_size": info['tick_size'],
                "tick_value": info['tick_value'],
            })
        return symbols

    async def check_and_refresh_contracts(self) -> int:
        """
        Check all cached contracts and refresh if needed (rollover).

        Should be called periodically (e.g., daily) to handle rollovers.

        Returns:
            Number of contracts refreshed
        """
        if not self._contract_resolver._initialized:
            if self._client:
                await self._contract_resolver.initialize(self._client)

        return await self._contract_resolver.refresh_all()

    def calculate_pnl(
        self,
        symbol: str,
        contracts: int,
        entry_price: float,
        exit_price: float
    ) -> float:
        """
        Calculate P&L for a trade.

        Args:
            symbol: Base symbol
            contracts: Number of contracts
            entry_price: Entry price
            exit_price: Exit price

        Returns:
            Dollar P&L value
        """
        price_change = exit_price - entry_price
        return self._contract_resolver.calculate_position_value(
            symbol, contracts, price_change
        )

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.

        Returns:
            Dict with account details (id, name, balance, equity, margin, etc.)

        Raises:
            RuntimeError: If not connected
        """
        if not self._client:
            raise RuntimeError("Not connected")

        account = self._client.account_info
        return {
            "id": str(getattr(account, 'id', '')) if account else "",
            "name": getattr(account, 'name', '') if account else "",
            "balance": float(getattr(account, 'balance', 0)) if account else 0.0,
            "equity": float(getattr(account, 'equity', getattr(account, 'balance', 0))) if account else 0.0,
            "margin": float(getattr(account, 'margin', 0)) if account else 0.0,
            "free_margin": float(getattr(account, 'free_margin', getattr(account, 'balance', 0))) if account else 0.0,
            "currency": getattr(account, 'currency', 'USD') if account else 'USD',
        }

    async def list_accounts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        List all accounts with status information.

        Uses SDK's list_accounts() to get all accounts and determine status
        based on canTrade, isVisible, and balance fields.

        Args:
            limit: Max accounts to return (sorted by ID desc, most recent first)

        Returns:
            List of account dicts with id, name, balance, status, etc.
            Status values: 'active', 'inactive', 'blown'

        Raises:
            RuntimeError: If not connected
        """
        if not self._client:
            raise RuntimeError("Not connected")

        try:
            accounts = await self._client.list_accounts()
        except Exception as e:
            logger.warning(f"list_accounts failed, falling back to account_info: {e}")
            # Fallback to single account
            info = await self.get_account_info()
            return [info] if info.get("id") else []

        # Sort by ID descending (most recent first) and limit
        sorted_accounts = sorted(accounts, key=lambda a: getattr(a, 'id', 0), reverse=True)
        limited_accounts = sorted_accounts[:limit] if limit > 0 else sorted_accounts

        result = []
        for acc in limited_accounts:
            acc_id = str(getattr(acc, 'id', ''))
            name = getattr(acc, 'name', '')
            balance = float(getattr(acc, 'balance', 0))
            can_trade = getattr(acc, 'canTrade', True)
            is_visible = getattr(acc, 'isVisible', True)
            simulated = getattr(acc, 'simulated', True)

            # Determine status based on canTrade and balance
            if not can_trade:
                status = 'blown' if balance < 100 else 'inactive'
            elif balance < 100:
                status = 'blown'
            else:
                status = 'active'

            result.append({
                "id": acc_id,
                "name": name,
                "balance": balance,
                "equity": balance,  # SDK doesn't provide separate equity
                "margin": 0.0,
                "free_margin": balance,
                "currency": "USD",
                "status": status,
                "can_trade": can_trade,
                "is_visible": is_visible,
                "is_live": not simulated,
                "is_active": can_trade,
            })

        return result

    async def get_trading_suite(self, instrument: str) -> Any:
        """
        Get or create TradingSuite for instrument.

        Args:
            instrument: Instrument symbol (e.g., "MNQ", "MES")

        Returns:
            TradingSuite instance for the instrument

        Raises:
            RuntimeError: If SDK not available or contract not found
        """
        import os

        if not SDK_AVAILABLE or TradingSuite is None:
            raise RuntimeError("SDK not available")

        # TradingSuite.create() looks for env vars, so set them from our credentials
        os.environ['PROJECT_X_USERNAME'] = self.username
        os.environ['PROJECT_X_API_KEY'] = self.api_key

        try:
            suite = await TradingSuite.create(instrument)
            if not suite:
                raise RuntimeError(f"TradingSuite.create returned None for {instrument}")
            if not hasattr(suite, 'instrument_id') or not suite.instrument_id:
                raise RuntimeError(f"TradingSuite has no instrument_id for {instrument}")
            logger.info(f"TradingSuite created for {instrument}: contract_id={suite.instrument_id}")
            return suite
        except Exception as e:
            logger.error(f"TradingSuite.create failed for '{instrument}': {e}")
            raise RuntimeError(f"Failed to find contract for {instrument}: {e}")

    async def search_instruments(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Search for instruments/contracts.

        Args:
            symbol: Symbol to search for (e.g., "MNQ")

        Returns:
            List of instrument dicts with id, symbol, description

        Raises:
            RuntimeError: If not connected
        """
        if not self._client:
            raise RuntimeError("Not connected")

        instruments = await self._client.search_instruments(symbol)
        return [
            {
                "id": str(getattr(inst, 'id', '')) if inst else "",
                "symbol": getattr(inst, 'name', symbol) if inst else symbol,
                "description": getattr(inst, 'description', '') if inst else '',
            }
            for inst in instruments
        ]

    async def place_market_order(
        self,
        instrument: str,
        side: str,  # "buy" or "sell"
        size: int,
    ) -> Dict[str, Any]:
        """
        Place market order via SDK.

        Args:
            instrument: Instrument symbol (TradingView format supported)
            side: "buy" or "sell"
            size: Number of contracts

        Returns:
            Dict with success, order_id, status
        """
        # Normalize TradingView symbols to ProjectX symbols
        instrument = normalize_symbol(instrument)
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            response = await suite.orders.place_market_order(
                contract_id=suite.instrument_id,
                side=side_int,
                size=size,
            )

            if not response:
                return {"success": False, "order_id": "", "status": "failed", "error": "No response from SDK"}

            success = getattr(response, 'success', False)
            order_id = str(getattr(response, 'orderId', ''))
            error_msg = getattr(response, 'errorMessage', None)

            if not success:
                logger.warning(f"ProjectX market order failed: {error_msg} (code: {getattr(response, 'errorCode', 'N/A')})")

            return {
                "success": success,
                "order_id": order_id,
                "status": "submitted" if success else "failed",
                "error": error_msg,
            }
        finally:
            await suite.disconnect()

    async def place_limit_order(
        self,
        instrument: str,
        side: str,
        size: int,
        limit_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place limit order via SDK.

        Args:
            instrument: Instrument symbol (TradingView format supported)
            side: "buy" or "sell"
            size: Number of contracts
            limit_price: Limit price for the order
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price

        Returns:
            Dict with success, order_id, status
        """
        instrument = normalize_symbol(instrument)
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            response = await suite.orders.place_limit_order(
                contract_id=suite.instrument_id,
                side=side_int,
                size=size,
                limit_price=limit_price,
            )

            if not response:
                return {"success": False, "order_id": "", "status": "failed", "error": "No response from SDK"}

            success = getattr(response, 'success', False)
            order_id = str(getattr(response, 'orderId', ''))
            error_msg = getattr(response, 'errorMessage', None)

            if not success:
                logger.warning(f"ProjectX limit order failed: {error_msg} (code: {getattr(response, 'errorCode', 'N/A')})")

            return {
                "success": success,
                "order_id": order_id,
                "status": "submitted" if success else "failed",
                "error": error_msg,
            }
        finally:
            await suite.disconnect()

    async def place_stop_order(
        self,
        instrument: str,
        side: str,
        size: int,
        stop_price: float,
    ) -> Dict[str, Any]:
        """
        Place stop order via SDK.

        A stop order becomes a market order when the stop price is reached.

        Args:
            instrument: Instrument symbol (TradingView format supported)
            side: "buy" or "sell"
            size: Number of contracts
            stop_price: Stop trigger price

        Returns:
            Dict with success, order_id, status
        """
        instrument = normalize_symbol(instrument)
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            response = await suite.orders.place_stop_order(
                contract_id=suite.instrument_id,
                side=side_int,
                size=size,
                stop_price=stop_price,
            )

            if not response:
                return {"success": False, "order_id": "", "status": "failed", "error": "No response from SDK"}

            success = getattr(response, 'success', False)
            order_id = str(getattr(response, 'orderId', ''))
            error_msg = getattr(response, 'errorMessage', None)

            if not success:
                logger.warning(f"ProjectX stop order failed: {error_msg} (code: {getattr(response, 'errorCode', 'N/A')})")

            return {
                "success": success,
                "order_id": order_id,
                "status": "submitted" if success else "failed",
                "error": error_msg,
            }
        except Exception as e:
            logger.error(f"Stop order failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    async def place_trailing_stop_order(
        self,
        instrument: str,
        side: str,
        size: int,
        trail_price: float,
    ) -> Dict[str, Any]:
        """
        Place trailing stop order via SDK.

        Args:
            instrument: Instrument symbol (TradingView format supported)
            side: "buy" or "sell"
            size: Number of contracts
            trail_price: Trail distance in ticks (max 1000)

        Returns:
            Dict with success, order_id, status
        """
        instrument = normalize_symbol(instrument)
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            response = await suite.orders.place_trailing_stop_order(
                contract_id=suite.instrument_id,
                side=side_int,
                size=size,
                trail_price=int(trail_price),  # In ticks
            )

            if not response:
                return {"success": False, "order_id": "", "status": "failed", "error": "No response from SDK"}

            success = getattr(response, 'success', False)
            order_id = str(getattr(response, 'orderId', ''))
            error_msg = getattr(response, 'errorMessage', None)

            if not success:
                logger.warning(f"ProjectX trailing stop order failed: {error_msg} (code: {getattr(response, 'errorCode', 'N/A')})")

            return {
                "success": success,
                "order_id": order_id,
                "status": "submitted" if success else "failed",
                "error": error_msg,
            }
        except Exception as e:
            logger.error(f"Trailing stop order failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel order via SDK.

        Note: SDK requires TradingSuite context. This is a limitation
        as we need to track which suite placed which order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Dict with success status and error if applicable
        """
        # SDK order cancellation requires instrument context
        return {"success": False, "error": "Order cancellation requires instrument context"}

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.

        Returns:
            List of position dicts with id, symbol, side, size, prices, pnl
        """
        if not self._client:
            raise RuntimeError("Not connected")

        try:
            # Use client's search_open_positions directly (SDK v3.0+)
            positions = await self._client.search_open_positions()

            result = []
            for pos in positions:
                if not pos:
                    continue

                # Get current price for PnL calculation
                current_price = float(getattr(pos, 'currentPrice', getattr(pos, 'current_price', 0)) or 0)
                entry_price = float(getattr(pos, 'avgPrice', getattr(pos, 'averagePrice', getattr(pos, 'entry_price', 0))) or 0)

                # Get symbol info for tick value
                symbol = getattr(pos, 'contractName', getattr(pos, 'symbol', ''))
                contract_info = self._contract_resolver.get_symbol_info(symbol) if symbol else None
                tick_value = float(contract_info.get('tick_value', 1.0)) if contract_info else 1.0

                # Handle pnl - prefer direct API values over calculated
                pnl_val = 0.0

                # First: Check for direct pnl/unrealizedPnl from API (most accurate)
                direct_pnl = getattr(pos, 'unrealizedPnl', None) or getattr(pos, 'pnl', None)
                if direct_pnl is not None and not callable(direct_pnl):
                    pnl_val = float(direct_pnl)

                # Second: Try SDK unrealized_pnl method with proper tick_value
                if pnl_val == 0.0:
                    pnl_attr = getattr(pos, 'unrealized_pnl', None)
                    if pnl_attr is not None:
                        if callable(pnl_attr):
                            try:
                                # Pass tick_value if method accepts it
                                import inspect
                                sig = inspect.signature(pnl_attr)
                                if len(sig.parameters) >= 2:
                                    pnl_val = float(pnl_attr(current_price, tick_value))
                                else:
                                    pnl_val = float(pnl_attr(current_price))
                            except Exception as pnl_err:
                                logger.debug(f"Error calculating PnL via method: {pnl_err}")
                                pnl_val = 0.0
                        else:
                            pnl_val = float(pnl_attr)

                # Third: Manual calculation as last resort
                if pnl_val == 0.0 and current_price > 0 and entry_price > 0:
                    pos_size = abs(float(getattr(pos, 'size', getattr(pos, 'qty', 0)) or 0))
                    pos_type = getattr(pos, 'type', None)
                    is_long = pos_type == 2 if pos_type is not None else (float(getattr(pos, 'size', 0) or 0) > 0)

                    tick_size = float(contract_info.get('tick_size', 0.01)) if contract_info else 0.01
                    if tick_size > 0:
                        price_diff = current_price - entry_price
                        ticks = price_diff / tick_size
                        pnl_val = ticks * tick_value * pos_size
                        if not is_long:
                            pnl_val = -pnl_val
                    logger.debug(f"Manual PnL calc for {symbol}: price_diff={current_price-entry_price}, tick_value={tick_value}, size={pos_size}, pnl={pnl_val}")

                # Determine side from 'type' attribute or size sign
                # Position type: 2 = long (buy), 0 = short (sell)
                # Fallback: positive size = long, negative = short
                pos_type = getattr(pos, 'type', None)
                pos_size = getattr(pos, 'size', getattr(pos, 'qty', 0)) or 0
                if pos_type is not None:
                    side = "buy" if pos_type == 2 else "sell"
                else:
                    side = "buy" if pos_size > 0 else "sell"

                result.append({
                    "id": str(getattr(pos, 'id', '')),
                    "contract_id": str(getattr(pos, 'contractId', getattr(pos, 'contract_id', ''))),
                    "symbol": getattr(pos, 'contractName', getattr(pos, 'symbol', '')),
                    "side": side,
                    "size": abs(float(pos_size)),
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": pnl_val,
                })
            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def close_position(
        self,
        instrument: str,
        position_id: str,
        size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Close position (full or partial).

        Args:
            instrument: Instrument symbol for the position
            position_id: Position ID to close
            size: Optional size for partial close

        Returns:
            Dict with success status and trade_id
        """
        suite = await self.get_trading_suite(instrument)
        try:
            # Get positions to find the one to close
            positions = await suite.positions.get_all_positions()

            for pos in positions:
                pos_id = str(getattr(pos, 'id', ''))
                contract_id = str(getattr(pos, 'contractId', getattr(pos, 'contract_id', '')))

                if pos_id == position_id or contract_id == position_id:
                    # Determine position side from 'type' attribute or size sign
                    # type=2 or positive size = long (bought), type=0 or negative size = short (sold)
                    # SDK order sides: 0=sell, 1=buy (empirically verified)
                    pos_type = getattr(pos, 'type', None)
                    pos_size = getattr(pos, 'size', 0)

                    # Long position (type=2 or positive size) needs sell order (side=0)
                    # Short position (type=0 or negative size) needs buy order (side=1)
                    is_long = pos_type == 2 or (pos_type is None and pos_size > 0)
                    close_side = 0 if is_long else 1  # SDK: 0=sell, 1=buy
                    close_size = size if size else abs(int(pos_size)) or 1

                    logger.info(f"Closing position {pos_id}: type={pos_type}, size={pos_size}, is_long={is_long}, close_side={close_side}, close_size={close_size}")

                    response = await suite.orders.place_market_order(
                        contract_id=suite.instrument_id,
                        side=close_side,
                        size=close_size,
                    )

                    return {
                        "success": True,
                        "trade_id": str(getattr(response, 'orderId', '')) if response else "",
                    }

            return {"success": False, "error": "Position not found"}
        finally:
            await suite.disconnect()

    async def close_all_positions(
        self,
        instrument: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Close all open positions (optionally filtered by instrument).

        Args:
            instrument: Optional instrument to filter positions

        Returns:
            Dict with success status, closed count, and results
        """
        if not self._client:
            raise RuntimeError("Not connected")

        try:
            # Get all open positions
            positions = await self._client.search_open_positions()

            if not positions:
                return {"success": True, "closed_count": 0, "total": 0, "results": []}

            results = []
            for pos in positions:
                pos_id = str(getattr(pos, 'id', ''))
                pos_symbol = getattr(pos, 'contractName', getattr(pos, 'symbol', ''))

                # Filter by instrument if provided
                if instrument and instrument.upper() not in pos_symbol.upper():
                    continue

                try:
                    # Determine the base symbol from the position
                    base_symbol = pos_symbol
                    # Extract base symbol from contract name (e.g., "MNQH2026" -> "MNQ")
                    for sym in ['MNQ', 'MES', 'MYM', 'M2K', 'MCL', 'MGC', 'MBT', 'ES', 'NQ', 'YM', 'RTY', 'CL', 'GC']:
                        if sym in pos_symbol.upper():
                            base_symbol = sym
                            break

                    result = await self.close_position(
                        instrument=base_symbol,
                        position_id=pos_id,
                    )
                    results.append({
                        "position_id": pos_id,
                        "symbol": pos_symbol,
                        "success": result.get("success", False),
                        "trade_id": result.get("trade_id", ""),
                        "error": result.get("error"),
                    })
                except Exception as e:
                    results.append({
                        "position_id": pos_id,
                        "symbol": pos_symbol,
                        "success": False,
                        "error": str(e),
                    })

            closed_count = sum(1 for r in results if r["success"])
            return {
                "success": closed_count > 0 or len(results) == 0,
                "closed_count": closed_count,
                "total": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"close_all_positions failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_market_data(
        self,
        instrument: str,
        days: int = 1,
        interval: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get historical market data.

        Args:
            instrument: Instrument symbol
            days: Number of days of data
            interval: Candle interval in minutes

        Returns:
            List of OHLCV data dicts
        """
        if not self._client:
            raise RuntimeError("Not connected")

        try:
            data = await self._client.get_bars(instrument, days=days, interval=interval)

            # Convert DataFrame to list of dicts
            # SDK uses Polars DataFrame, use to_dicts() method
            if hasattr(data, 'to_dicts'):
                return data.to_dicts()
            # Fallback for pandas DataFrame
            elif hasattr(data, 'to_dict'):
                return data.to_dict(orient='records')
            return []
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return []

    # =========================================================================
    # Advanced Order Features
    # =========================================================================

    async def place_bracket_order(
        self,
        instrument: str,
        side: str,
        size: int,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place bracket order (OCO) with stop loss and take profit.

        Uses SDK's native place_bracket_order which handles SL/TP atomically.
        For market orders, this creates a bracket that triggers on position fill.

        SDK signature:
        place_bracket_order(contract_id, side, size, entry_price, stop_loss_price,
                          take_profit_price, entry_type='limit', account_id=None)

        Args:
            instrument: Instrument symbol (TradingView format supported)
            side: "buy" or "sell"
            size: Number of contracts
            entry_price: Entry price (None for market order)
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Dict with success, order_id, status
        """
        instrument = normalize_symbol(instrument)
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1
            logger.info(f"place_bracket_order called: instrument={instrument}, side={side}, size={size}, entry_price={entry_price}, stop_loss={stop_loss}, take_profit={take_profit}")

            # If we have both SL and TP, use native bracket order
            if stop_loss and take_profit:
                # SDK's place_bracket_order handles this atomically
                entry_type = 'market' if entry_price is None else 'limit'
                logger.info(f"Using SDK place_bracket_order with entry_type={entry_type}, contract_id={suite.instrument_id}")
                response = await suite.orders.place_bracket_order(
                    contract_id=suite.instrument_id,
                    side=side_int,
                    size=size,
                    entry_price=entry_price,  # None for market
                    stop_loss_price=stop_loss,
                    take_profit_price=take_profit,
                    entry_type=entry_type,
                )
                logger.info(f"SDK place_bracket_order response: {response}")
                order_id = getattr(response, 'orderId', getattr(response, 'order_id', '')) if response else ""
                return {
                    "success": getattr(response, 'success', True) if response else True,
                    "order_id": str(order_id),
                    "status": "submitted",
                    "bracket": True,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                }

            # If only SL or only TP, place order first then add protection
            # For market orders with partial protection, we need to:
            # 1. Place market order
            # 2. Wait for fill
            # 3. Add SL/TP to the resulting position
            if entry_price:
                main_order = await suite.orders.place_limit_order(
                    contract_id=suite.instrument_id,
                    side=side_int,
                    size=size,
                    limit_price=entry_price,
                )
            else:
                main_order = await suite.orders.place_market_order(
                    contract_id=suite.instrument_id,
                    side=side_int,
                    size=size,
                )

            order_id = getattr(main_order, 'orderId', getattr(main_order, 'order_id', '')) if main_order else ""
            execution_id = getattr(main_order, 'executionId', getattr(main_order, 'execution_id', '')) if main_order else ""

            result = {
                "success": getattr(main_order, 'success', True) if main_order else True,
                "order_id": str(order_id) if order_id else str(execution_id),
                "status": "submitted",
            }

            # For limit orders (pending), we can add SL/TP to the order
            if entry_price and order_id:
                if stop_loss:
                    try:
                        await suite.orders.add_stop_loss(order_id, stop_loss)
                        result["stop_loss"] = stop_loss
                    except Exception as e:
                        logger.warning(f"Failed to add stop loss to order: {e}")

                if take_profit:
                    try:
                        await suite.orders.add_take_profit(order_id, take_profit)
                        result["take_profit"] = take_profit
                    except Exception as e:
                        logger.warning(f"Failed to add take profit to order: {e}")
            else:
                # Market order filled immediately - need to add protection to position
                # The position_id should match the execution_id or we need to query positions
                if stop_loss or take_profit:
                    result["note"] = "Market order filled. Use add_stop_loss_to_position/add_take_profit_to_position for protection."
                    result["execution_id"] = str(execution_id)

            return result
        except Exception as e:
            logger.error(f"Bracket order failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    async def create_order_chain(
        self,
        instrument: str,
        orders: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create an order chain (sequence of orders).

        Args:
            instrument: Instrument symbol
            orders: List of order dicts with type, side, size, price, etc.

        Returns:
            Dict with success and chain_id
        """
        suite = await self.get_trading_suite(instrument)
        try:
            chain = suite.order_chain()
            for order in orders:
                order_type = order.get("type", "market")
                side = 0 if order.get("side", "buy").lower() == "buy" else 1
                size = order.get("size", 1)

                if order_type == "market":
                    chain.place_market_order(side=side, size=size)
                elif order_type == "limit":
                    chain.place_limit_order(
                        side=side,
                        size=size,
                        limit_price=order.get("price", 0)
                    )

            result = await chain.execute()
            return {
                "success": True,
                "chain_id": str(getattr(result, 'chainId', '')) if result else "",
            }
        except Exception as e:
            logger.error(f"Order chain failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    async def add_stop_loss_to_order(
        self,
        instrument: str,
        order_id: str,
        stop_loss_price: float,
    ) -> Dict[str, Any]:
        """Add stop loss to existing order."""
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.orders.add_stop_loss(order_id, stop_loss_price)
            return {"success": True}
        except Exception as e:
            logger.error(f"Add stop loss failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    async def add_take_profit_to_order(
        self,
        instrument: str,
        order_id: str,
        take_profit_price: float,
    ) -> Dict[str, Any]:
        """Add take profit to existing order."""
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.orders.add_take_profit(order_id, take_profit_price)
            return {"success": True}
        except Exception as e:
            logger.error(f"Add take profit failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    async def cancel_all_orders(self, instrument: str) -> Dict[str, Any]:
        """Cancel all orders for instrument."""
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.orders.cancel_all_orders()
            return {"success": True}
        except Exception as e:
            logger.error(f"Cancel all orders failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await suite.disconnect()

    # =========================================================================
    # Position Analytics and Portfolio Features
    # =========================================================================

    async def get_portfolio_metrics(self, instruments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get portfolio metrics across multiple instruments.

        Args:
            instruments: Optional list of instruments (None = all positions)

        Returns:
            Dict with portfolio metrics (total_pnl, win_rate, sharpe_ratio, etc.)
        """
        if not self._client:
            raise RuntimeError("Not connected")

        if not SDK_AVAILABLE or TradingSuite is None:
            return {}

        try:
            # Use first instrument or default
            instrument = instruments[0] if instruments else "MNQ"
            suite = await TradingSuite.create(instrument)

            # Get portfolio PnL
            portfolio_pnl = await suite.positions.calculate_portfolio_pnl()

            # Get all positions for metrics
            positions = await suite.positions.get_all_positions()

            total_pnl = float(getattr(portfolio_pnl, 'total_pnl', 0)) if portfolio_pnl else 0.0
            win_count = sum(1 for pos in positions if getattr(pos, 'unrealized_pnl', 0) > 0)
            win_rate = (win_count / len(positions)) * 100 if positions else 0.0

            await suite.disconnect()

            return {
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "total_positions": len(positions),
                "winning_positions": win_count,
                "losing_positions": len(positions) - win_count,
            }
        except Exception as e:
            logger.error(f"Error getting portfolio metrics: {e}")
            return {}

    async def get_position_analytics(
        self,
        instrument: str,
        position_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed position analytics.

        Args:
            instrument: Instrument symbol
            position_id: Optional position ID (None = all positions for instrument)

        Returns:
            Dict with position analytics
        """
        suite = await self.get_trading_suite(instrument)
        try:
            if position_id:
                position = await suite.positions.get_position(position_id)
                if position:
                    pnl = await suite.positions.calculate_position_pnl(position_id)
                    return {
                        "position_id": str(getattr(position, 'id', '')),
                        "symbol": getattr(position, 'symbol', ''),
                        "side": "buy" if getattr(position, 'side', 0) == 0 else "sell",
                        "size": float(getattr(position, 'size', 0)),
                        "entry_price": float(getattr(position, 'entry_price', 0)),
                        "current_price": float(getattr(position, 'current_price', 0)),
                        "unrealized_pnl": float(getattr(pnl, 'unrealized_pnl', 0)) if pnl else 0.0,
                    }
            else:
                # Get all positions analytics
                positions = await suite.positions.get_all_positions()
                return {
                    "positions": [
                        {
                            "id": str(getattr(pos, 'id', '')),
                            "symbol": getattr(pos, 'symbol', ''),
                            "side": "buy" if getattr(pos, 'side', 0) == 0 else "sell",
                            "size": float(getattr(pos, 'size', 0)),
                            "entry_price": float(getattr(pos, 'entry_price', 0)),
                            "current_price": float(getattr(pos, 'current_price', 0)),
                            "unrealized_pnl": float(getattr(pos, 'unrealized_pnl', 0)),
                        }
                        for pos in positions
                    ]
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting position analytics: {e}")
            return {}
        finally:
            await suite.disconnect()

    async def get_position_history(
        self,
        instrument: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get position history (closed positions).

        Args:
            instrument: Instrument symbol
            days: Number of days to look back

        Returns:
            List of historical position dicts
        """
        suite = await self.get_trading_suite(instrument)
        try:
            history = await suite.positions.get_position_history(days=days)
            return [
                {
                    "id": str(getattr(pos, 'id', '')) if pos else "",
                    "symbol": getattr(pos, 'symbol', '') if pos else '',
                    "side": "buy" if getattr(pos, 'side', 0) == 0 else "sell",
                    "size": float(getattr(pos, 'size', 0)) if pos else 0,
                    "entry_price": float(getattr(pos, 'entry_price', 0)) if pos else 0.0,
                    "exit_price": float(getattr(pos, 'exit_price', 0)) if pos else 0.0,
                    "realized_pnl": float(getattr(pos, 'realized_pnl', 0)) if pos else 0.0,
                    "entry_time": str(getattr(pos, 'entry_time', '')) if pos else '',
                    "exit_time": str(getattr(pos, 'exit_time', '')) if pos else '',
                }
                for pos in history
            ]
        except Exception as e:
            logger.error(f"Error getting position history: {e}")
            return []
        finally:
            await suite.disconnect()

    async def calculate_position_size(
        self,
        instrument: str,
        risk_amount: float,
        stop_loss_price: float,
        entry_price: float,
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size based on risk.

        Args:
            instrument: Instrument symbol
            risk_amount: Amount to risk in dollars
            stop_loss_price: Stop loss price
            entry_price: Entry price

        Returns:
            Dict with calculated position size
        """
        suite = await self.get_trading_suite(instrument)
        try:
            size = await suite.positions.calculate_position_size(
                risk_amount=risk_amount,
                stop_loss_price=stop_loss_price,
                entry_price=entry_price,
            )
            return {
                "position_size": float(size) if size else 0.0,
                "risk_amount": risk_amount,
                "stop_loss_price": stop_loss_price,
                "entry_price": entry_price,
            }
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {}
        finally:
            await suite.disconnect()

    # =========================================================================
    # OrderBook (Level 2 Market Depth)
    # =========================================================================

    async def get_orderbook(
        self,
        instrument: str,
        depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Get Level 2 orderbook (market depth).

        Args:
            instrument: Instrument symbol
            depth: Number of price levels to retrieve

        Returns:
            Dict with bids, asks, and market depth data
        """
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.connect()
            orderbook = suite.orderbook

            # Get orderbook data
            bids = []
            asks = []

            # SDK orderbook provides bid/ask data
            if hasattr(orderbook, 'get_bids'):
                bids_data = orderbook.get_bids(depth=depth)
                bids = [
                    {"price": float(bid.get("price", 0)), "size": float(bid.get("size", 0))}
                    for bid in bids_data
                ] if isinstance(bids_data, list) else []

            if hasattr(orderbook, 'get_asks'):
                asks_data = orderbook.get_asks(depth=depth)
                asks = [
                    {"price": float(ask.get("price", 0)), "size": float(ask.get("size", 0))}
                    for ask in asks_data
                ] if isinstance(asks_data, list) else []

            return {
                "symbol": instrument,
                "bids": bids,
                "asks": asks,
                "best_bid": bids[0]["price"] if bids else 0.0,
                "best_ask": asks[0]["price"] if asks else 0.0,
                "spread": (asks[0]["price"] - bids[0]["price"]) if (bids and asks) else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting orderbook: {e}")
            return {}
        finally:
            await suite.disconnect()

    # =========================================================================
    # Real-time Data Streaming
    # =========================================================================

    async def subscribe_realtime_data(
        self,
        instrument: str,
        callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Subscribe to real-time market data for instrument.

        Args:
            instrument: Instrument symbol
            callback: Optional callback function for data updates

        Returns:
            Dict with subscription status
        """
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.connect()
            data_manager = suite.data

            # Subscribe to real-time updates
            if callback:
                suite.on('price_update', callback)
                suite.on('position_update', callback)
                suite.on('order_update', callback)

            return {
                "success": True,
                "instrument": instrument,
                "subscribed": True,
            }
        except Exception as e:
            logger.error(f"Error subscribing to real-time data: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Don't disconnect - keep connection for real-time updates
            pass

    # =========================================================================
    # Session Statistics and Analytics
    # =========================================================================

    async def get_session_statistics(
        self,
        instrument: str,
        session_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get session statistics and analytics.

        Args:
            instrument: Instrument symbol
            session_type: Optional session type filter

        Returns:
            Dict with session statistics
        """
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.connect()

            if session_type:
                suite.set_session_type(session_type)

            stats = await suite.get_session_statistics()

            return {
                "session_type": session_type or "all",
                "total_trades": int(getattr(stats, 'total_trades', 0)) if stats else 0,
                "winning_trades": int(getattr(stats, 'winning_trades', 0)) if stats else 0,
                "losing_trades": int(getattr(stats, 'losing_trades', 0)) if stats else 0,
                "win_rate": float(getattr(stats, 'win_rate', 0)) if stats else 0.0,
                "total_pnl": float(getattr(stats, 'total_pnl', 0)) if stats else 0.0,
                "average_win": float(getattr(stats, 'average_win', 0)) if stats else 0.0,
                "average_loss": float(getattr(stats, 'average_loss', 0)) if stats else 0.0,
                "profit_factor": float(getattr(stats, 'profit_factor', 0)) if stats else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {}
        finally:
            await suite.disconnect()

    async def get_performance_stats(self, instrument: str) -> Dict[str, Any]:
        """
        Get performance statistics.

        Args:
            instrument: Instrument symbol

        Returns:
            Dict with performance metrics (Sharpe ratio, max drawdown, etc.)
        """
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.connect()
            stats = await suite.get_stats()

            return {
                "sharpe_ratio": float(getattr(stats, 'sharpe_ratio', 0)) if stats else 0.0,
                "max_drawdown": float(getattr(stats, 'max_drawdown', 0)) if stats else 0.0,
                "total_return": float(getattr(stats, 'total_return', 0)) if stats else 0.0,
                "volatility": float(getattr(stats, 'volatility', 0)) if stats else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}
        finally:
            await suite.disconnect()

    # =========================================================================
    # Technical Indicators
    # =========================================================================

    async def calculate_technical_indicators(
        self,
        instrument: str,
        days: int = 30,
        interval: int = 5,
    ) -> Dict[str, Any]:
        """
        Calculate technical indicators for instrument.

        SDK indicator functions expect Polars DataFrames and return DataFrames
        with new columns added.

        Args:
            instrument: Instrument symbol
            days: Number of days of data
            interval: Candle interval in minutes

        Returns:
            Dict with calculated indicators (latest values)
        """
        if not self._client:
            raise RuntimeError("Not connected")

        try:
            # Get market data (returns Polars DataFrame)
            data = await self._client.get_bars(instrument, days=days, interval=interval)

            if data is None or len(data) == 0:
                return {}

            indicators = {}
            num_rows = len(data)

            # RSI - column name includes period: 'rsi_14'
            if num_rows >= 14:
                try:
                    rsi_df = calculate_rsi(data, column='close', period=14)
                    if 'rsi_14' in rsi_df.columns:
                        rsi_values = rsi_df['rsi_14'].to_list()
                        indicators["rsi"] = rsi_values[-1] if rsi_values else None
                        indicators["rsi_history"] = rsi_values[-20:]  # Last 20 values
                except Exception as e:
                    logger.warning(f"RSI calculation failed: {e}")

            # MACD - columns: 'macd', 'macd_signal', 'macd_histogram'
            if num_rows >= 26:
                try:
                    macd_df = calculate_macd(data, column='close')
                    if 'macd' in macd_df.columns:
                        indicators["macd"] = macd_df['macd'].to_list()[-1]
                    if 'macd_signal' in macd_df.columns:
                        indicators["macd_signal"] = macd_df['macd_signal'].to_list()[-1]
                    if 'macd_histogram' in macd_df.columns:
                        indicators["macd_histogram"] = macd_df['macd_histogram'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"MACD calculation failed: {e}")

            # Bollinger Bands - columns: 'bb_middle_20', 'bb_upper_20', 'bb_lower_20'
            if num_rows >= 20:
                try:
                    bb_df = calculate_bollinger_bands(data, column='close', period=20)
                    if 'bb_upper_20' in bb_df.columns:
                        indicators["bb_upper"] = bb_df['bb_upper_20'].to_list()[-1]
                    if 'bb_middle_20' in bb_df.columns:
                        indicators["bb_middle"] = bb_df['bb_middle_20'].to_list()[-1]
                    if 'bb_lower_20' in bb_df.columns:
                        indicators["bb_lower"] = bb_df['bb_lower_20'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"Bollinger Bands calculation failed: {e}")

            # ATR - column: 'atr_14'
            if num_rows >= 14:
                try:
                    atr_df = calculate_atr(data, period=14)
                    if 'atr_14' in atr_df.columns:
                        indicators["atr"] = atr_df['atr_14'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"ATR calculation failed: {e}")

            # EMA - columns: 'ema_20', 'ema_50'
            if num_rows >= 20:
                try:
                    ema20_df = calculate_ema(data, column='close', period=20)
                    if 'ema_20' in ema20_df.columns:
                        indicators["ema_20"] = ema20_df['ema_20'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"EMA 20 calculation failed: {e}")

            if num_rows >= 50:
                try:
                    ema50_df = calculate_ema(data, column='close', period=50)
                    if 'ema_50' in ema50_df.columns:
                        indicators["ema_50"] = ema50_df['ema_50'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"EMA 50 calculation failed: {e}")

            # SMA - columns: 'sma_20', 'sma_50'
            if num_rows >= 20:
                try:
                    sma20_df = calculate_sma(data, column='close', period=20)
                    if 'sma_20' in sma20_df.columns:
                        indicators["sma_20"] = sma20_df['sma_20'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"SMA 20 calculation failed: {e}")

            if num_rows >= 50:
                try:
                    sma50_df = calculate_sma(data, column='close', period=50)
                    if 'sma_50' in sma50_df.columns:
                        indicators["sma_50"] = sma50_df['sma_50'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"SMA 50 calculation failed: {e}")

            # Stochastic - columns: 'stoch_k_14', 'stoch_d_3'
            if num_rows >= 14:
                try:
                    stoch_df = calculate_stochastic(data, k_period=14, d_period=3)
                    if 'stoch_k_14' in stoch_df.columns:
                        indicators["stoch_k"] = stoch_df['stoch_k_14'].to_list()[-1]
                    if 'stoch_d_3' in stoch_df.columns:
                        indicators["stoch_d"] = stoch_df['stoch_d_3'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"Stochastic calculation failed: {e}")

            # ADX - columns: 'plus_di_14', 'minus_di_14', 'adx_14'
            if num_rows >= 14:
                try:
                    adx_df = calculate_adx(data, period=14)
                    if 'adx_14' in adx_df.columns:
                        indicators["adx"] = adx_df['adx_14'].to_list()[-1]
                    if 'plus_di_14' in adx_df.columns:
                        indicators["plus_di"] = adx_df['plus_di_14'].to_list()[-1]
                    if 'minus_di_14' in adx_df.columns:
                        indicators["minus_di"] = adx_df['minus_di_14'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"ADX calculation failed: {e}")

            # CCI - column: 'cci_20'
            if num_rows >= 20:
                try:
                    cci_df = calculate_commodity_channel_index(data, period=20)
                    if 'cci_20' in cci_df.columns:
                        indicators["cci"] = cci_df['cci_20'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"CCI calculation failed: {e}")

            # Williams %R - column: 'williams_r_14'
            if num_rows >= 14:
                try:
                    wr_df = calculate_williams_r(data, period=14)
                    if 'williams_r_14' in wr_df.columns:
                        indicators["williams_r"] = wr_df['williams_r_14'].to_list()[-1]
                except Exception as e:
                    logger.warning(f"Williams %R calculation failed: {e}")

            # Add current price for reference
            indicators["current_price"] = data['close'].to_list()[-1]
            indicators["data_points"] = num_rows

            return indicators

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}

    # =========================================================================
    # Risk Management
    # =========================================================================

    async def get_risk_analysis(
        self,
        instrument: str,
    ) -> Dict[str, Any]:
        """
        Get risk analysis for positions.

        Args:
            instrument: Instrument symbol

        Returns:
            Dict with risk metrics
        """
        suite = await self.get_trading_suite(instrument)
        try:
            await suite.connect()
            risk_manager = suite.risk_manager

            # Get risk analysis
            if hasattr(risk_manager, 'get_risk_analysis'):
                analysis = await risk_manager.get_risk_analysis()
                return {
                    "max_position_size": float(getattr(analysis, 'max_position_size', 0)) if analysis else 0.0,
                    "current_risk": float(getattr(analysis, 'current_risk', 0)) if analysis else 0.0,
                    "risk_per_trade": float(getattr(analysis, 'risk_per_trade', 0)) if analysis else 0.0,
                    "max_drawdown": float(getattr(analysis, 'max_drawdown', 0)) if analysis else 0.0,
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting risk analysis: {e}")
            return {}
        finally:
            await suite.disconnect()
