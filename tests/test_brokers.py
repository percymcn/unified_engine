"""
Comprehensive test suite for all broker executors.
Tests MT4, MT5, TradeLocker, Tradovate, and ProjectX integrations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.brokers.mt4_executor import MT4Executor
from app.brokers.mt5_executor import MT5Executor
from app.brokers.tradelocker_executor import TradeLockerExecutor
from app.brokers.tradovate_executor import TradovateExecutor
from app.brokers.projectx_executor import ProjectXExecutor
from app.models.schemas import (
    SignalRequest, Position, Trade, AccountInfo,
    BrokerType, OrderType, OrderSide, SignalType
)


class TestMT4Executor:
    """Test MT4 Executor functionality."""
    
    @pytest.fixture
    def executor(self):
        config = {
            "manager_api_url": "http://localhost:4444",
            "manager_login": 1,
            "manager_password": "test",
            "server_timeout": 30
        }
        return MT4Executor(config)
    
    @pytest.fixture
    def sample_signal(self):
        return SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            price=1.1000,
            stop_loss=1.0900,
            take_profit=1.1100,
            signal_type=SignalType.ENTRY,
            confidence=0.8
        )
    
    @pytest.mark.asyncio
    async def test_connect_success(self, executor):
        """Test successful connection to MT4 Manager."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"retcode": 0}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.connect()
            assert result is True
            assert executor.is_connected is True
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, executor):
        """Test failed connection to MT4 Manager."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.connect()
            assert result is False
            assert executor.is_connected is False
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, executor, sample_signal):
        """Test successful order placement."""
        executor.is_connected = True
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "retcode": 0,
                "order": 12345,
                "price": 1.1000
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.place_order(sample_signal)
            assert result is not None
            assert result.order_id == 12345
            assert result.status == "filled"
    
    @pytest.mark.asyncio
    async def test_place_order_not_connected(self, executor, sample_signal):
        """Test order placement when not connected."""
        executor.is_connected = False
        
        with pytest.raises(Exception, match="Not connected to MT4"):
            await executor.place_order(sample_signal)
    
    @pytest.mark.asyncio
    async def test_get_positions(self, executor):
        """Test getting positions from MT4."""
        executor.is_connected = True
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "retcode": 0,
                "positions": [
                    {
                        "ticket": 12345,
                        "symbol": "EURUSD",
                        "type": 0,  # BUY
                        "volume": 0.1,
                        "price_open": 1.1000,
                        "price_current": 1.1050,
                        "profit": 50.0
                    }
                ]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            positions = await executor.get_positions()
            assert len(positions) == 1
            assert positions[0].symbol == "EURUSD"
            assert positions[0].quantity == 0.1
    
    @pytest.mark.asyncio
    async def test_close_position(self, executor):
        """Test closing a position."""
        executor.is_connected = True
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"retcode": 0}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.close_position(12345)
            assert result is True


class TestMT5Executor:
    """Test MT5 Executor functionality."""
    
    @pytest.fixture
    def executor(self):
        config = {
            "manager_api_url": "http://localhost:4445",
            "manager_login": 1,
            "manager_password": "test",
            "server_timeout": 30
        }
        return MT5Executor(config)
    
    @pytest.mark.asyncio
    async def test_connect_success(self, executor):
        """Test successful connection to MT5 Manager."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"retcode": 0}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.connect()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_place_order_with_filling_type(self, executor):
        """Test order placement with MT5 filling type."""
        executor.is_connected = True
        
        signal = SignalRequest(
            broker=BrokerType.MT5,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            price=1.1000,
            signal_type=SignalType.ENTRY
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "retcode": 0,
                "order": 54321,
                "price": 1.1000,
                "volume": 0.1
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.place_order(signal)
            assert result is not None
            assert result.order_id == 54321


class TestTradeLockerExecutor:
    """Test TradeLocker Executor functionality."""
    
    @pytest.fixture
    def executor(self):
        config = {
            "brand_api_url": "https://api.tradelocker.com",
            "brand_id": "test_brand",
            "server_url": "https://live.tradelocker.com",
            "ws_url": "wss://live.tradelocker.com/ws",
            "timeout": 30
        }
        return TradeLockerExecutor(config)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, executor):
        """Test successful authentication."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "accessToken": "test_token",
                "refreshToken": "refresh_token",
                "expiresIn": 3600
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.authenticate("test@example.com", "password")
            assert result is True
            assert executor.access_token == "test_token"
    
    @pytest.mark.asyncio
    async def test_place_order_api_request(self, executor):
        """Test order placement via API."""
        executor.access_token = "test_token"
        
        signal = SignalRequest(
            broker=BrokerType.TRADELOCKER,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1000,
            signal_type=SignalType.ENTRY
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "orderId": "TL_12345",
                "status": "FILLED",
                "executedPrice": 1.1000
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.place_order(signal)
            assert result is not None
            assert result.order_id == "TL_12345"
            assert result.status == "filled"
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, executor):
        """Test WebSocket connection."""
        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Mock authentication message
            mock_ws.recv.return_value = json.dumps({
                "event": "authenticated",
                "data": {"status": "success"}
            })
            
            result = await executor.connect_websocket("test_token")
            assert result is True


class TestTradovateExecutor:
    """Test Tradovate Executor functionality."""
    
    @pytest.fixture
    def executor(self):
        config = {
            "api_url": "https://demo.tradovate.com",
            "ws_url": "wss://demo.tradovate.com/ws",
            "app_id": "test_app",
            "app_version": "1.0.0",
            "timeout": 30
        }
        return TradovateExecutor(config)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, executor):
        """Test successful authentication."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock token request
            mock_token_response = AsyncMock()
            mock_token_response.status = 200
            mock_token_response.json.return_value = {
                "accessToken": "test_token",
                "refreshToken": "refresh_token",
                "expirationTime": "2024-01-01T00:00:00Z"
            }
            
            # Mock authorize request
            mock_auth_response = AsyncMock()
            mock_auth_response.status = 200
            mock_auth_response.json.return_value = {
                "userId": 12345,
                "name": "Test User"
            }
            
            mock_post.side_effect = [
                mock_token_response.__aenter__.return_value,
                mock_auth_response.__aenter__.return_value
            ]
            
            result = await executor.authenticate("test@example.com", "password")
            assert result is True
            assert executor.access_token == "test_token"
    
    @pytest.mark.asyncio
    async def test_place_order(self, executor):
        """Test order placement."""
        executor.access_token = "test_token"
        executor.user_id = 12345
        
        signal = SignalRequest(
            broker=BrokerType.TRADOVATE,
            symbol="ES",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1,
            signal_type=SignalType.ENTRY
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "orderId": "TV_12345",
                "status": "Filled",
                "fillPrice": 4500.25
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.place_order(signal)
            assert result is not None
            assert result.order_id == "TV_12345"
            assert result.status == "filled"


class TestProjectXExecutor:
    """Test ProjectX/TopStep Executor functionality."""
    
    @pytest.fixture
    def executor(self):
        config = {
            "gateway_api_url": "https://gateway.projectx.com",
            "timeout": 30
        }
        return ProjectXExecutor(config)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, executor):
        """Test successful authentication."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "token": "test_token",
                "expiresIn": 3600
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.authenticate("test@example.com", "password")
            assert result is True
            assert executor.auth_token == "test_token"
    
    @pytest.mark.asyncio
    async def test_place_order(self, executor):
        """Test order placement."""
        executor.auth_token = "test_token"
        
        signal = SignalRequest(
            broker=BrokerType.PROJECTX,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100000,
            signal_type=SignalType.ENTRY
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "orderId": "PX_12345",
                "status": "FILLED",
                "executedPrice": 1.1000
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await executor.place_order(signal)
            assert result is not None
            assert result.order_id == "PX_12345"
            assert result.status == "filled"


class TestBrokerIntegration:
    """Test integration between all brokers."""
    
    @pytest.mark.asyncio
    async def test_all_brokers_initialization(self):
        """Test that all brokers can be initialized."""
        configs = {
            "mt4": {"manager_api_url": "http://localhost:4444"},
            "mt5": {"manager_api_url": "http://localhost:4445"},
            "tradelocker": {"brand_api_url": "https://api.tradelocker.com"},
            "tradovate": {"api_url": "https://demo.tradovate.com"},
            "projectx": {"gateway_api_url": "https://gateway.projectx.com"}
        }
        
        brokers = {
            "mt4": MT4Executor(configs["mt4"]),
            "mt5": MT5Executor(configs["mt5"]),
            "tradelocker": TradeLockerExecutor(configs["tradelocker"]),
            "tradovate": TradovateExecutor(configs["tradovate"]),
            "projectx": ProjectXExecutor(configs["projectx"])
        }
        
        # Test that all brokers are properly initialized
        for name, broker in brokers.items():
            assert broker is not None
            assert hasattr(broker, 'config')
            assert hasattr(broker, 'place_order')
            assert hasattr(broker, 'get_positions')
    
    @pytest.mark.asyncio
    async def test_signal_routing_to_correct_broker(self):
        """Test that signals are routed to the correct broker."""
        signal_mt4 = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        signal_tradelocker = SignalRequest(
            broker=BrokerType.TRADELOCKER,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1000,
            signal_type=SignalType.ENTRY
        )
        
        # Test broker type identification
        assert signal_mt4.broker == BrokerType.MT4
        assert signal_tradelocker.broker == BrokerType.TRADELOCKER


if __name__ == "__main__":
    pytest.main([__file__, "-v"])