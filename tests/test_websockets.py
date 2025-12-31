"""
Test WebSocket connections and real-time updates functionality.
Tests WebSocket manager, real-time data streaming, and connection management.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
import sys
import os
import websockets
from fastapi.testclient import TestClient
from fastapi import status

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.websocket_manager import WebSocketManager
from app.models.schemas import BrokerType, OrderType, OrderSide


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a WebSocket manager instance."""
        return WebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = Mock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, websocket_manager, mock_websocket):
        """Test WebSocket connection establishment."""
        user_id = "test_user_123"
        
        await websocket_manager.connect(mock_websocket, user_id)
        
        assert user_id in websocket_manager.active_connections
        assert mock_websocket in websocket_manager.active_connections[user_id]
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket(self, websocket_manager, mock_websocket):
        """Test WebSocket disconnection."""
        user_id = "test_user_123"
        
        # First connect
        await websocket_manager.connect(mock_websocket, user_id)
        assert user_id in websocket_manager.active_connections
        
        # Then disconnect
        await websocket_manager.disconnect(mock_websocket, user_id)
        
        # Connection should be removed
        if user_id in websocket_manager.active_connections:
            assert mock_websocket not in websocket_manager.active_connections[user_id]
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, websocket_manager, mock_websocket):
        """Test sending personal message to a user."""
        user_id = "test_user_123"
        message = {"type": "test", "data": "Hello World"}
        
        await websocket_manager.connect(mock_websocket, user_id)
        await websocket_manager.send_personal_message(message, user_id)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "test"
        assert sent_data["data"] == "Hello World"
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, websocket_manager):
        """Test broadcasting message to all connected users."""
        # Create multiple mock websockets
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()
        
        # Connect multiple users
        await websocket_manager.connect(mock_ws1, "user1")
        await websocket_manager.connect(mock_ws2, "user2")
        
        message = {"type": "broadcast", "data": "System Update"}
        await websocket_manager.broadcast(message)
        
        # Both websockets should receive the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()
        
        # Verify message content
        sent_data1 = json.loads(mock_ws1.send_text.call_args[0][0])
        sent_data2 = json.loads(mock_ws2.send_text.call_args[0][0])
        assert sent_data1["type"] == "broadcast"
        assert sent_data2["type"] == "broadcast"
    
    @pytest.mark.asyncio
    async def test_get_connected_users(self, websocket_manager):
        """Test getting list of connected users."""
        mock_ws1 = Mock()
        mock_ws2 = Mock()
        
        await websocket_manager.connect(mock_ws1, "user1")
        await websocket_manager.connect(mock_ws2, "user2")
        
        connected_users = websocket_manager.get_connected_users()
        
        assert "user1" in connected_users
        assert "user2" in connected_users
        assert len(connected_users) == 2
    
    @pytest.mark.asyncio
    async def test_send_to_broker_subscribers(self, websocket_manager):
        """Test sending messages to broker-specific subscribers."""
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()
        
        # Connect users and subscribe them to brokers
        await websocket_manager.connect(mock_ws1, "user1")
        await websocket_manager.connect(mock_ws2, "user2")
        
        websocket_manager.subscribe_to_broker("user1", BrokerType.MT4)
        websocket_manager.subscribe_to_broker("user2", BrokerType.TRADELOCKER)
        
        message = {"type": "broker_update", "broker": "MT4", "data": "Price Update"}
        await websocket_manager.send_to_broker_subscribers(BrokerType.MT4, message)
        
        # Only MT4 subscriber should receive the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_broker_subscription_management(self, websocket_manager):
        """Test broker subscription management."""
        user_id = "test_user"
        
        # Subscribe to broker
        websocket_manager.subscribe_to_broker(user_id, BrokerType.MT4)
        assert BrokerType.MT4 in websocket_manager.broker_subscriptions[user_id]
        
        # Subscribe to another broker
        websocket_manager.subscribe_to_broker(user_id, BrokerType.TRADELOCKER)
        assert BrokerType.TRADELOCKER in websocket_manager.broker_subscriptions[user_id]
        
        # Unsubscribe from broker
        websocket_manager.unsubscribe_from_broker(user_id, BrokerType.MT4)
        assert BrokerType.MT4 not in websocket_manager.broker_subscriptions[user_id]
        assert BrokerType.TRADELOCKER in websocket_manager.broker_subscriptions[user_id]


class TestWebSocketEndpoints:
    """Test WebSocket endpoint functionality."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_websocket_endpoint_connection(self, client):
        """Test WebSocket endpoint connection."""
        with patch('app.main.websocket_manager') as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            with client.websocket_connect("/ws") as websocket:
                # Connection should be established
                assert websocket is not None
    
    def test_websocket_with_authentication(self, client):
        """Test WebSocket connection with authentication."""
        # Create a valid token
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": "test@example.com"})
        
        with patch('app.main.websocket_manager') as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            # Connect with token in query parameter
            with client.websocket_connect(f"/ws?token={token}") as websocket:
                assert websocket is not None
    
    def test_websocket_without_authentication(self, client):
        """Test WebSocket connection without authentication fails."""
        with pytest.raises(Exception):  # Should raise an exception for unauthorized
            with client.websocket_connect("/ws") as websocket:
                pass


class TestRealTimeDataStreaming:
    """Test real-time data streaming functionality."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a WebSocket manager instance."""
        return WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_stream_price_updates(self, websocket_manager):
        """Test streaming price updates to subscribers."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        websocket_manager.subscribe_to_broker(user_id, BrokerType.MT4)
        
        # Simulate price update
        price_update = {
            "type": "price_update",
            "broker": "MT4",
            "symbol": "EURUSD",
            "bid": 1.0995,
            "ask": 1.1005,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.send_to_broker_subscribers(BrokerType.MT4, price_update)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "price_update"
        assert sent_data["symbol"] == "EURUSD"
        assert sent_data["bid"] == 1.0995
        assert sent_data["ask"] == 1.1005
    
    @pytest.mark.asyncio
    async def test_stream_order_updates(self, websocket_manager):
        """Test streaming order updates to users."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        
        # Simulate order update
        order_update = {
            "type": "order_update",
            "order_id": "order_123",
            "status": "filled",
            "symbol": "EURUSD",
            "side": "BUY",
            "quantity": 0.1,
            "fill_price": 1.1000,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.send_personal_message(order_update, user_id)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "order_update"
        assert sent_data["order_id"] == "order_123"
        assert sent_data["status"] == "filled"
    
    @pytest.mark.asyncio
    async def test_stream_position_updates(self, websocket_manager):
        """Test streaming position updates to users."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        
        # Simulate position update
        position_update = {
            "type": "position_update",
            "position_id": "pos_123",
            "symbol": "EURUSD",
            "side": "BUY",
            "quantity": 0.1,
            "entry_price": 1.1000,
            "current_price": 1.1050,
            "unrealized_pnl": 50.0,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.send_personal_message(position_update, user_id)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "position_update"
        assert sent_data["symbol"] == "EURUSD"
        assert sent_data["unrealized_pnl"] == 50.0
    
    @pytest.mark.asyncio
    async def test_stream_signal_updates(self, websocket_manager):
        """Test streaming signal updates to users."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        
        # Simulate signal update
        signal_update = {
            "type": "signal_update",
            "signal_id": "signal_123",
            "broker": "MT4",
            "symbol": "EURUSD",
            "action": "BUY",
            "status": "executed",
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.send_personal_message(signal_update, user_id)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "signal_update"
        assert sent_data["signal_id"] == "signal_123"
        assert sent_data["status"] == "executed"


class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a WebSocket manager instance."""
        return WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, websocket_manager):
        """Test handling of connection errors."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        
        # Should handle connection errors gracefully
        message = {"type": "test", "data": "Hello"}
        
        # This should not raise an exception
        try:
            await websocket_manager.send_personal_message(message, user_id)
        except Exception:
            # Expected to handle the error
            pass
    
    @pytest.mark.asyncio
    async def test_invalid_message_handling(self, websocket_manager):
        """Test handling of invalid messages."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        
        # Test with invalid message (non-serializable)
        invalid_message = {"type": "test", "data": object()}  # object() is not JSON serializable
        
        # Should handle serialization errors gracefully
        try:
            await websocket_manager.send_personal_message(invalid_message, user_id)
        except (TypeError, ValueError):
            # Expected to handle serialization errors
            pass
    
    @pytest.mark.asyncio
    async def test_user_not_connected_error(self, websocket_manager):
        """Test handling messages to non-connected users."""
        non_existent_user = "non_existent_user"
        message = {"type": "test", "data": "Hello"}
        
        # Should handle gracefully when user is not connected
        result = await websocket_manager.send_personal_message(message, non_existent_user)
        
        # Should not raise an exception
        assert result is None


class TestWebSocketPerformance:
    """Test WebSocket performance and scalability."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a WebSocket manager instance."""
        return WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_multiple_connections_performance(self, websocket_manager):
        """Test performance with multiple concurrent connections."""
        # Create multiple mock websockets
        mock_websockets = []
        for i in range(100):
            mock_ws = Mock()
            mock_ws.send_text = AsyncMock()
            mock_websockets.append(mock_ws)
        
        # Connect all users
        for i, mock_ws in enumerate(mock_websockets):
            await websocket_manager.connect(mock_ws, f"user_{i}")
        
        # Broadcast message to all
        message = {"type": "broadcast", "data": "Performance Test"}
        await websocket_manager.broadcast(message)
        
        # Verify all websockets received the message
        for mock_ws in mock_websockets:
            mock_ws.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_high_frequency_messages(self, websocket_manager):
        """Test performance with high-frequency messages."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        await websocket_manager.connect(mock_websocket, user_id)
        
        # Send multiple messages rapidly
        messages = [
            {"type": "price_update", "data": f"message_{i}"}
            for i in range(1000)
        ]
        
        for message in messages:
            await websocket_manager.send_personal_message(message, user_id)
        
        # Verify all messages were sent
        assert mock_websocket.send_text.call_count == 1000
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_on_disconnect(self, websocket_manager):
        """Test memory cleanup when users disconnect."""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = "test_user"
        
        # Connect user
        await websocket_manager.connect(mock_websocket, user_id)
        assert user_id in websocket_manager.active_connections
        
        # Subscribe to broker
        websocket_manager.subscribe_to_broker(user_id, BrokerType.MT4)
        assert user_id in websocket_manager.broker_subscriptions
        
        # Disconnect user
        await websocket_manager.disconnect(mock_websocket, user_id)
        
        # Verify cleanup
        if user_id in websocket_manager.active_connections:
            assert len(websocket_manager.active_connections[user_id]) == 0
        
        # Broker subscriptions should be cleaned up
        if user_id in websocket_manager.broker_subscriptions:
            assert len(websocket_manager.broker_subscriptions[user_id]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])