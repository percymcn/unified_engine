"""
Test webhook signal processing with mock data.
Tests TradingView and TrailHacker webhook processing.
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

from app.services.signal_processor import SignalProcessor
from app.models.schemas import (
    SignalRequest, WebhookSignal, BrokerType, OrderType, 
    OrderSide, SignalType, WebhookType
)


class TestWebhookSignalProcessing:
    """Test webhook signal processing functionality."""
    
    @pytest.fixture
    def signal_processor(self):
        """Create a signal processor instance for testing."""
        return SignalProcessor()
    
    @pytest.fixture
    def tradingview_webhook_data(self):
        """Sample TradingView webhook data."""
        return {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1,
            "stop_loss": 1.0900,
            "take_profit": 1.1100,
            "strategy": "MA_Cross",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    
    @pytest.fixture
    def trailhacker_webhook_data(self):
        """Sample TrailHacker webhook data."""
        return {
            "ticker": "ES",
            "order_action": "BOT",
            "order_type": "MKT",
            "quantity": 1,
            "price": 4500.25,
            "stop": 4480.00,
            "target": 4520.00,
            "strategy": "TrailHacker",
            "time": "2024-01-01T12:00:00Z"
        }
    
    @pytest.mark.asyncio
    async def test_process_tradingview_webhook(self, signal_processor, tradingview_webhook_data):
        """Test processing TradingView webhook data."""
        with patch.object(signal_processor, 'process_signal') as mock_process:
            mock_process.return_value = {
                "success": True,
                "signal_id": "tv_signal_123",
                "order_id": "order_456"
            }
            
            result = await signal_processor.process_webhook_signal(
                WebhookType.TRADINGVIEW,
                tradingview_webhook_data
            )
            
            assert result["success"] is True
            assert "signal_id" in result
            assert "order_id" in result
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_trailhacker_webhook(self, signal_processor, trailhacker_webhook_data):
        """Test processing TrailHacker webhook data."""
        with patch.object(signal_processor, 'process_signal') as mock_process:
            mock_process.return_value = {
                "success": True,
                "signal_id": "th_signal_789",
                "order_id": "order_101"
            }
            
            result = await signal_processor.process_webhook_signal(
                WebhookType.TRAILHACKER,
                trailhacker_webhook_data
            )
            
            assert result["success"] is True
            assert "signal_id" in result
            assert "order_id" in result
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tradingview_signal_conversion(self, signal_processor, tradingview_webhook_data):
        """Test conversion of TradingView webhook to SignalRequest."""
        webhook_signal = WebhookSignal(
            webhook_type=WebhookType.TRADINGVIEW,
            data=tradingview_webhook_data,
            timestamp=datetime.now()
        )
        
        signal_request = signal_processor.convert_webhook_to_signal(webhook_signal)
        
        assert signal_request.symbol == "EURUSD"
        assert signal_request.side == OrderSide.BUY
        assert signal_request.order_type == OrderType.MARKET
        assert signal_request.quantity == 0.1
        assert signal_request.price == 1.1000
        assert signal_request.stop_loss == 1.0900
        assert signal_request.take_profit == 1.1100
        assert signal_request.signal_type == SignalType.ENTRY
    
    @pytest.mark.asyncio
    async def test_trailhacker_signal_conversion(self, signal_processor, trailhacker_webhook_data):
        """Test conversion of TrailHacker webhook to SignalRequest."""
        webhook_signal = WebhookSignal(
            webhook_type=WebhookType.TRAILHACKER,
            data=trailhacker_webhook_data,
            timestamp=datetime.now()
        )
        
        signal_request = signal_processor.convert_webhook_to_signal(webhook_signal)
        
        assert signal_request.symbol == "ES"
        assert signal_request.side == OrderSide.BUY  # BOT maps to BUY
        assert signal_request.order_type == OrderType.MARKET  # MKT maps to MARKET
        assert signal_request.quantity == 1
        assert signal_request.price == 4500.25
        assert signal_request.stop_loss == 4480.00
        assert signal_request.take_profit == 4520.00
        assert signal_request.signal_type == SignalType.ENTRY
    
    @pytest.mark.asyncio
    async def test_invalid_webhook_data(self, signal_processor):
        """Test handling of invalid webhook data."""
        invalid_data = {
            "invalid": "data"
        }
        
        with pytest.raises(Exception, match="Invalid webhook data"):
            await signal_processor.process_webhook_signal(
                WebhookType.TRADINGVIEW,
                invalid_data
            )
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, signal_processor):
        """Test handling of missing required fields."""
        incomplete_data = {
            "symbol": "EURUSD",
            # Missing action, price, quantity
        }
        
        with pytest.raises(Exception, match="Missing required fields"):
            await signal_processor.process_webhook_signal(
                WebhookType.TRADINGVIEW,
                incomplete_data
            )
    
    @pytest.mark.asyncio
    async def test_signal_validation(self, signal_processor):
        """Test signal validation before processing."""
        invalid_signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="",  # Empty symbol
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0,  # Zero quantity
            signal_type=SignalType.ENTRY
        )
        
        with pytest.raises(Exception, match="Invalid signal"):
            await signal_processor.validate_signal(invalid_signal)
    
    @pytest.mark.asyncio
    async def test_broker_routing(self, signal_processor):
        """Test that signals are routed to correct brokers."""
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
        
        # Mock broker executors
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_mt4, \
             patch('app.brokers.tradelocker_executor.TradeLockerExecutor') as mock_tl:
            
            mock_mt4_instance = AsyncMock()
            mock_tl_instance = AsyncMock()
            mock_mt4.return_value = mock_mt4_instance
            mock_tl.return_value = mock_tl_instance
            
            # Test MT4 routing
            await signal_processor.route_signal_to_broker(signal_mt4)
            mock_mt4_instance.place_order.assert_called_once_with(signal_mt4)
            
            # Test TradeLocker routing
            await signal_processor.route_signal_to_broker(signal_tradelocker)
            mock_tl_instance.place_order.assert_called_once_with(signal_tradelocker)
    
    @pytest.mark.asyncio
    async def test_risk_management_validation(self, signal_processor):
        """Test risk management validation."""
        # Test position size limits
        large_position_signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100.0,  # Very large position
            signal_type=SignalType.ENTRY
        )
        
        with patch.object(signal_processor, 'check_position_size_limit') as mock_check:
            mock_check.return_value = False
            
            with pytest.raises(Exception, match="Position size exceeds limit"):
                await signal_processor.validate_risk_limits(large_position_signal)
    
    @pytest.mark.asyncio
    async def test_signal_retry_mechanism(self, signal_processor):
        """Test signal retry mechanism on failure."""
        signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        with patch.object(signal_processor, 'route_signal_to_broker') as mock_route:
            # First two attempts fail, third succeeds
            mock_route.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                {"success": True, "order_id": "retry_order"}
            ]
            
            result = await signal_processor.process_signal_with_retry(signal, max_retries=3)
            
            assert result["success"] is True
            assert result["order_id"] == "retry_order"
            assert mock_route.call_count == 3
    
    @pytest.mark.asyncio
    async def test_webhook_authentication(self, signal_processor):
        """Test webhook authentication."""
        webhook_data = {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1
        }
        
        # Test with valid API key
        with patch.object(signal_processor, 'validate_webhook_key') as mock_validate:
            mock_validate.return_value = True
            
            result = await signal_processor.authenticate_webhook(
                "valid_api_key",
                webhook_data
            )
            
            assert result is True
            mock_validate.assert_called_once_with("valid_api_key")
        
        # Test with invalid API key
        with patch.object(signal_processor, 'validate_webhook_key') as mock_validate:
            mock_validate.return_value = False
            
            with pytest.raises(Exception, match="Invalid webhook key"):
                await signal_processor.authenticate_webhook(
                    "invalid_api_key",
                    webhook_data
                )
    
    @pytest.mark.asyncio
    async def test_signal_logging_and_audit(self, signal_processor):
        """Test signal logging and audit trail."""
        signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        with patch.object(signal_processor, 'log_signal') as mock_log, \
             patch.object(signal_processor, 'route_signal_to_broker') as mock_route:
            
            mock_route.return_value = {"success": True, "order_id": "audit_order"}
            
            result = await signal_processor.process_signal(signal)
            
            # Verify logging was called
            mock_log.assert_called()
            
            # Verify audit trail is created
            assert "audit_trail" in result
            assert result["audit_trail"]["signal_id"] is not None
            assert result["audit_trail"]["timestamp"] is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_processing(self, signal_processor):
        """Test concurrent processing of multiple signals."""
        signals = [
            SignalRequest(
                broker=BrokerType.MT4,
                symbol=f"EURUSD_{i}",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=0.1,
                signal_type=SignalType.ENTRY
            )
            for i in range(5)
        ]
        
        with patch.object(signal_processor, 'route_signal_to_broker') as mock_route:
            mock_route.return_value = {"success": True, "order_id": f"order_{i}"}
            
            # Process all signals concurrently
            tasks = [signal_processor.process_signal(signal) for signal in signals]
            results = await asyncio.gather(*tasks)
            
            # Verify all signals were processed
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["success"] is True
                assert f"order_{i}" in result.get("order_id", "")
            
            # Verify all brokers were called
            assert mock_route.call_count == 5


class TestWebhookEndpoints:
    """Test webhook endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_tradingview_webhook_endpoint(self):
        """Test TradingView webhook endpoint."""
        from app.routers.webhooks import tradingview_webhook
        
        webhook_data = {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1
        }
        
        with patch('app.services.signal_processor.SignalProcessor.process_webhook_signal') as mock_process:
            mock_process.return_value = {"success": True, "signal_id": "tv_123"}
            
            result = await tradingview_webhook(webhook_data)
            
            assert result["status"] == "success"
            assert "signal_id" in result
    
    @pytest.mark.asyncio
    async def test_trailhacker_webhook_endpoint(self):
        """Test TrailHacker webhook endpoint."""
        from app.routers.webhooks import trailhacker_webhook
        
        webhook_data = {
            "ticker": "ES",
            "order_action": "BOT",
            "order_type": "MKT",
            "quantity": 1,
            "price": 4500.25
        }
        
        with patch('app.services.signal_processor.SignalProcessor.process_webhook_signal') as mock_process:
            mock_process.return_value = {"success": True, "signal_id": "th_456"}
            
            result = await trailhacker_webhook(webhook_data)
            
            assert result["status"] == "success"
            assert "signal_id" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])