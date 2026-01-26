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

        Args:
            instrument: Instrument symbol
            side: "buy" or "sell"
            size: Number of contracts
            entry_price: Entry price (None for market)
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Dict with success, order_id, status
        """
        suite = await self.get_trading_suite(instrument)
        try:
            side_int = 0 if side.lower() == "buy" else 1

            # Place main order
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

            order_id = getattr(main_order, 'orderId', '') if main_order else ""

            # Add stop loss if provided
            if stop_loss and order_id:
                await suite.orders.add_stop_loss(order_id, stop_loss)

            # Add take profit if provided
            if take_profit and order_id:
                await suite.orders.add_take_profit(order_id, take_profit)

            return {
                "success": True,
                "order_id": str(order_id),
                "status": "submitted",
            }
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

        Args:
            instrument: Instrument symbol
            days: Number of days of data
            interval: Candle interval in minutes

        Returns:
            Dict with calculated indicators
        """
        if not self._client:
            raise RuntimeError("Not connected")

        try:
            # Get market data
            data = await self._client.get_bars(instrument, days=days, interval=interval)

            if not hasattr(data, 'to_dict'):
                return {}

            # Convert to list for calculations
            closes = data['close'].tolist() if 'close' in data.columns else []
            highs = data['high'].tolist() if 'high' in data.columns else []
            lows = data['low'].tolist() if 'low' in data.columns else []
            volumes = data['volume'].tolist() if 'volume' in data.columns else []

            if not closes:
                return {}

            # Calculate indicators
            indicators = {}

            # RSI
            if len(closes) >= 14:
                indicators["rsi"] = calculate_rsi(closes, period=14)

            # MACD
            if len(closes) >= 26:
                macd_result = calculate_macd(closes)
                indicators["macd"] = macd_result.get("macd", []) if isinstance(macd_result, dict) else []
                indicators["macd_signal"] = macd_result.get("signal", []) if isinstance(macd_result, dict) else []
                indicators["macd_histogram"] = macd_result.get("histogram", []) if isinstance(macd_result, dict) else []

            # Bollinger Bands
            if len(closes) >= 20:
                bb_result = calculate_bollinger_bands(closes, period=20)
                indicators["bb_upper"] = bb_result.get("upper", []) if isinstance(bb_result, dict) else []
                indicators["bb_middle"] = bb_result.get("middle", []) if isinstance(bb_result, dict) else []
                indicators["bb_lower"] = bb_result.get("lower", []) if isinstance(bb_result, dict) else []

            # ATR
            if len(highs) >= 14 and len(lows) >= 14:
                indicators["atr"] = calculate_atr(highs, lows, closes, period=14)

            # EMA
            if len(closes) >= 20:
                indicators["ema_20"] = calculate_ema(closes, period=20)
                indicators["ema_50"] = calculate_ema(closes, period=50) if len(closes) >= 50 else []

            # SMA
            if len(closes) >= 20:
                indicators["sma_20"] = calculate_sma(closes, period=20)
                indicators["sma_50"] = calculate_sma(closes, period=50) if len(closes) >= 50 else []

            # Stochastic
            if len(highs) >= 14 and len(lows) >= 14:
                stoch_result = calculate_stochastic(highs, lows, closes, period=14)
                indicators["stoch_k"] = stoch_result.get("k", []) if isinstance(stoch_result, dict) else []
                indicators["stoch_d"] = stoch_result.get("d", []) if isinstance(stoch_result, dict) else []

            # OBV
            if volumes and len(closes) == len(volumes):
                indicators["obv"] = calculate_obv(closes, volumes)

            # VWAP
            if volumes and len(closes) == len(volumes):
                indicators["vwap"] = calculate_vwap(highs, lows, closes, volumes)

            # ADX
            if len(highs) >= 14 and len(lows) >= 14:
                indicators["adx"] = calculate_adx(highs, lows, closes, period=14)

            # CCI
            if len(highs) >= 20 and len(lows) >= 20:
                indicators["cci"] = calculate_commodity_channel_index(highs, lows, closes, period=20)

            # Williams %R
            if len(highs) >= 14 and len(lows) >= 14:
                indicators["williams_r"] = calculate_williams_r(highs, lows, closes, period=14)

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
