"""
ProjectX SDK Service
Wraps official project-x-py SDK for use in Tradeflow.

Uses the official project-x-py SDK for TopStep/ProjectX Gateway API integration.
Provides async-first interface matching existing executor patterns.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import SDK - graceful fallback if not installed
try:
    from project_x_py import ProjectX, TradingSuite
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ProjectX = None
    TradingSuite = None
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

    @property
    def is_connected(self) -> bool:
        """Check if SDK is connected."""
        return self._is_connected and self._client is not None

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

    async def get_trading_suite(self, instrument: str) -> Any:
        """
        Get or create TradingSuite for instrument.

        Args:
            instrument: Instrument symbol (e.g., "MNQ", "MES")

        Returns:
            TradingSuite instance for the instrument
        """
        if not SDK_AVAILABLE or TradingSuite is None:
            raise RuntimeError("SDK not available")

        suite = await TradingSuite.create(instrument)
        return suite

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
            instrument: Instrument symbol
            side: "buy" or "sell"
            size: Number of contracts

        Returns:
            Dict with success, order_id, status
        """
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            response = await suite.orders.place_market_order(
                contract_id=suite.instrument_id,
                side=side_int,
                size=size,
            )

            return {
                "success": getattr(response, 'success', True) if response else True,
                "order_id": str(getattr(response, 'orderId', '')) if response else "",
                "status": "submitted",
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
            instrument: Instrument symbol
            side: "buy" or "sell"
            size: Number of contracts
            limit_price: Limit price for the order
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price

        Returns:
            Dict with success, order_id, status
        """
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            response = await suite.orders.place_limit_order(
                contract_id=suite.instrument_id,
                side=side_int,
                size=size,
                limit_price=limit_price,
            )

            return {
                "success": getattr(response, 'success', True) if response else True,
                "order_id": str(getattr(response, 'orderId', '')) if response else "",
                "status": "submitted",
            }
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

        if not SDK_AVAILABLE or TradingSuite is None:
            return []

        try:
            # Use a common instrument to initialize suite for position access
            suite = await TradingSuite.create("MNQ")
            positions = await suite.positions.get_all_positions()
            await suite.disconnect()

            return [
                {
                    "id": str(getattr(pos, 'id', '')) if pos else "",
                    "contract_id": str(getattr(pos, 'contract_id', '')) if pos else "",
                    "symbol": getattr(pos, 'symbol', '') if pos else '',
                    "side": "buy" if getattr(pos, 'side', 0) == 0 else "sell",
                    "size": float(getattr(pos, 'size', 0)) if pos else 0,
                    "entry_price": float(getattr(pos, 'entry_price', 0)) if pos else 0.0,
                    "current_price": float(getattr(pos, 'current_price', 0)) if pos else 0.0,
                    "unrealized_pnl": float(getattr(pos, 'unrealized_pnl', 0)) if pos else 0.0,
                }
                for pos in positions
            ]
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
                contract_id = str(getattr(pos, 'contract_id', ''))

                if pos_id == position_id or contract_id == position_id:
                    # Place opposite order to close
                    pos_side = getattr(pos, 'side', 0)
                    close_side = 1 if pos_side == 0 else 0  # Opposite side
                    close_size = size if size else int(getattr(pos, 'size', 1))

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
            if hasattr(data, 'to_dict'):
                return data.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return []
