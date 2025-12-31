"""
End-to-end trading workflow tests.
Tests complete trading workflows from signal to execution across all brokers.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.signal_processor import SignalProcessor
from app.models.schemas import (
    SignalRequest, BrokerType, OrderType, OrderSide, SignalType,
    WebhookType, WebhookSignal
)


class TestEndToEndTradingWorkflow:
    """Test complete end-to-end trading workflows."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def signal_processor(self):
        """Create a signal processor instance."""
        return SignalProcessor()
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": "test@example.com"})
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_complete_tradingview_workflow(self, signal_processor):
        """Test complete workflow from TradingView webhook to order execution."""
        # Step 1: Receive TradingView webhook
        webhook_data = {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1,
            "stop_loss": 1.0900,
            "take_profit": 1.1100,
            "strategy": "MA_Cross",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        # Step 2: Convert webhook to signal
        webhook_signal = WebhookSignal(
            webhook_type=WebhookType.TRADINGVIEW,
            data=webhook_data,
            timestamp=datetime.now()
        )
        
        signal_request = signal_processor.convert_webhook_to_signal(webhook_signal)
        
        assert signal_request.symbol == "EURUSD"
        assert signal_request.side == OrderSide.BUY
        assert signal_request.quantity == 0.1
        
        # Step 3: Route to broker (mock MT4)
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # Mock successful order execution
            mock_trade = Mock()
            mock_trade.order_id = "mt4_order_123"
            mock_trade.status = "filled"
            mock_trade.fill_price = 1.1000
            mock_executor.place_order.return_value = mock_trade
            
            # Step 4: Execute signal
            result = await signal_processor.process_signal(signal_request)
            
            assert result["success"] is True
            assert "order_id" in result
            assert result["order_id"] == "mt4_order_123"
            
            # Verify broker was called
            mock_executor.place_order.assert_called_once_with(signal_request)
    
    @pytest.mark.asyncio
    async def test_complete_trailhacker_workflow(self, signal_processor):
        """Test complete workflow from TrailHacker webhook to order execution."""
        # Step 1: Receive TrailHacker webhook
        webhook_data = {
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
        
        # Step 2: Convert webhook to signal
        webhook_signal = WebhookSignal(
            webhook_type=WebhookType.TRAILHACKER,
            data=webhook_data,
            timestamp=datetime.now()
        )
        
        signal_request = signal_processor.convert_webhook_to_signal(webhook_signal)
        
        assert signal_request.symbol == "ES"
        assert signal_request.side == OrderSide.BUY
        assert signal_request.quantity == 1
        
        # Step 3: Route to broker (mock Tradovate)
        with patch('app.brokers.tradovate_executor.TradovateExecutor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # Mock successful order execution
            mock_trade = Mock()
            mock_trade.order_id = "tv_order_456"
            mock_trade.status = "filled"
            mock_trade.fill_price = 4500.25
            mock_executor.place_order.return_value = mock_trade
            
            # Step 4: Execute signal
            result = await signal_processor.process_signal(signal_request)
            
            assert result["success"] is True
            assert "order_id" in result
            assert result["order_id"] == "tv_order_456"
    
    @pytest.mark.asyncio
    async def test_multi_broker_signal_distribution(self, signal_processor):
        """Test signal distribution to multiple brokers."""
        signal_request = SignalRequest(
            broker=BrokerType.MT4,  # Primary broker
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        # Mock multiple brokers
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_mt4, \
             patch('app.brokers.mt5_executor.MT5Executor') as mock_mt5, \
             patch('app.brokers.tradelocker_executor.TradeLockerExecutor') as mock_tl:
            
            mock_mt4_executor = AsyncMock()
            mock_mt5_executor = AsyncMock()
            mock_tl_executor = AsyncMock()
            
            mock_mt4.return_value = mock_mt4_executor
            mock_mt5.return_value = mock_mt5_executor
            mock_tl.return_value = mock_tl_executor
            
            # Mock successful executions
            mock_mt4_executor.place_order.return_value = Mock(order_id="mt4_123")
            mock_mt5_executor.place_order.return_value = Mock(order_id="mt5_456")
            mock_tl_executor.place_order.return_value = Mock(order_id="tl_789")
            
            # Execute signal on primary broker
            result = await signal_processor.process_signal(signal_request)
            
            assert result["success"] is True
            assert result["order_id"] == "mt4_123"
            
            # Verify only primary broker was called
            mock_mt4_executor.place_order.assert_called_once()
            mock_mt5_executor.place_order.assert_not_called()
            mock_tl_executor.place_order.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_signal_with_risk_management(self, signal_processor):
        """Test signal processing with risk management validation."""
        # Create a signal that exceeds risk limits
        large_signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=10.0,  # Large position
            signal_type=SignalType.ENTRY
        )
        
        with patch.object(signal_processor, 'validate_risk_limits') as mock_validate:
            mock_validate.side_effect = Exception("Position size exceeds daily limit")
            
            # Should fail risk validation
            with pytest.raises(Exception, match="Position size exceeds daily limit"):
                await signal_processor.process_signal(large_signal)
    
    @pytest.mark.asyncio
    async def test_signal_retry_on_failure(self, signal_processor):
        """Test signal retry mechanism on broker failure."""
        signal_request = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # First two attempts fail, third succeeds
            mock_executor.place_order.side_effect = [
                Exception("Network timeout"),
                Exception("Broker unavailable"),
                Mock(order_id="retry_order_789", status="filled")
            ]
            
            # Process with retry
            result = await signal_processor.process_signal_with_retry(
                signal_request, 
                max_retries=3
            )
            
            assert result["success"] is True
            assert result["order_id"] == "retry_order_789"
            assert mock_executor.place_order.call_count == 3
    
    @pytest.mark.asyncio
    async def test_position_management_workflow(self, signal_processor):
        """Test complete position management workflow."""
        # Step 1: Open position
        entry_signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            price=1.1000,
            stop_loss=1.0900,
            take_profit=1.1100,
            signal_type=SignalType.ENTRY
        )
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # Mock position opening
            mock_trade = Mock()
            mock_trade.order_id = "position_123"
            mock_trade.status = "filled"
            mock_trade.fill_price = 1.1000
            mock_executor.place_order.return_value = mock_trade
            
            # Open position
            entry_result = await signal_processor.process_signal(entry_signal)
            assert entry_result["success"] is True
            
            # Step 2: Close position
            exit_signal = SignalRequest(
                broker=BrokerType.MT4,
                symbol="EURUSD",
                order_type=OrderType.MARKET,
                side=OrderSide.SELL,
                quantity=0.1,
                signal_type=SignalType.EXIT,
                related_order_id="position_123"
            )
            
            # Mock position closing
            mock_exit_trade = Mock()
            mock_exit_trade.order_id = "exit_456"
            mock_exit_trade.status = "filled"
            mock_exit_trade.fill_price = 1.1050
            mock_executor.place_order.return_value = mock_exit_trade
            
            # Close position
            exit_result = await signal_processor.process_signal(exit_signal)
            assert exit_result["success"] is True
            assert exit_result["order_id"] == "exit_456"
            
            # Verify both entry and exit were processed
            assert mock_executor.place_order.call_count == 2
    
    @pytest.mark.asyncio
    async def test_webhook_to_position_workflow(self, client, auth_headers):
        """Test complete workflow from webhook to position management."""
        webhook_data = {
            "symbol": "EURUSD",
            "action": "buy",
            "price": 1.1000,
            "quantity": 0.1,
            "stop_loss": 1.0900,
            "take_profit": 1.1100
        }
        
        with patch('app.services.signal_processor.SignalProcessor.process_webhook_signal') as mock_process:
            # Mock signal processing
            mock_process.return_value = {
                "success": True,
                "signal_id": "webhook_signal_123",
                "order_id": "webhook_order_456",
                "position_id": "position_789"
            }
            
            # Send webhook
            response = client.post(
                "/webhooks/tradingview",
                json=webhook_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, signal_processor):
        """Test error recovery in trading workflow."""
        signal_request = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker, \
             patch('app.brokers.mt5_executor.MT5Executor') as mock_backup_broker:
            
            mock_executor = AsyncMock()
            mock_backup_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            mock_backup_broker.return_value = mock_backup_executor
            
            # Primary broker fails
            mock_executor.place_order.side_effect = Exception("Primary broker down")
            
            # Backup broker succeeds
            mock_backup_trade = Mock()
            mock_backup_trade.order_id = "backup_order_123"
            mock_backup_trade.status = "filled"
            mock_backup_executor.place_order.return_value = mock_backup_trade
            
            # Process with fallback
            result = await signal_processor.process_signal_with_fallback(
                signal_request,
                fallback_brokers=[BrokerType.MT5]
            )
            
            assert result["success"] is True
            assert result["order_id"] == "backup_order_123"
            assert result["broker"] == "MT5"  # Fallback broker was used
    
    @pytest.mark.asyncio
    async def test_audit_trail_workflow(self, signal_processor):
        """Test audit trail creation throughout workflow."""
        signal_request = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.1,
            signal_type=SignalType.ENTRY
        )
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker, \
             patch.object(signal_processor, 'create_audit_trail') as mock_audit:
            
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            mock_trade = Mock()
            mock_trade.order_id = "audited_order_123"
            mock_trade.status = "filled"
            mock_executor.place_order.return_value = mock_trade
            
            # Mock audit trail creation
            mock_audit.return_value = {
                "audit_id": "audit_456",
                "timestamp": datetime.now().isoformat(),
                "signal_id": "signal_789",
                "order_id": "audited_order_123"
            }
            
            # Process signal
            result = await signal_processor.process_signal(signal_request)
            
            # Verify audit trail was created
            mock_audit.assert_called_once()
            assert "audit_trail" in result
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_processing(self, signal_processor):
        """Test processing multiple signals concurrently."""
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
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # Mock successful executions
            def mock_place_order(signal):
                mock_trade = Mock()
                mock_trade.order_id = f"concurrent_order_{signal.symbol}"
                mock_trade.status = "filled"
                return mock_trade
            
            mock_executor.place_order.side_effect = mock_place_order
            
            # Process all signals concurrently
            tasks = [signal_processor.process_signal(signal) for signal in signals]
            results = await asyncio.gather(*tasks)
            
            # Verify all signals were processed successfully
            assert len(results) == 5
            for result in results:
                assert result["success"] is True
                assert "order_id" in result
            
            # Verify all orders were placed
            assert mock_executor.place_order.call_count == 5


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_scalping_strategy_workflow(self, signal_processor):
        """Test scalping strategy with multiple quick entries/exits."""
        # Quick entry
        entry_signal = SignalRequest(
            broker=BrokerType.MT4,
            symbol="EURUSD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.01,
            signal_type=SignalType.ENTRY,
            strategy="scalping"
        )
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # Mock quick entry and exit
            mock_entry = Mock()
            mock_entry.order_id = "scalp_entry_123"
            mock_entry.status = "filled"
            mock_entry.fill_price = 1.1000
            
            mock_exit = Mock()
            mock_exit.order_id = "scalp_exit_456"
            mock_exit.status = "filled"
            mock_exit.fill_price = 1.1005
            
            mock_executor.place_order.side_effect = [mock_entry, mock_exit]
            
            # Execute scalping workflow
            entry_result = await signal_processor.process_signal(entry_signal)
            assert entry_result["success"] is True
            
            # Quick exit after small profit
            exit_signal = SignalRequest(
                broker=BrokerType.MT4,
                symbol="EURUSD",
                order_type=OrderType.MARKET,
                side=OrderSide.SELL,
                quantity=0.01,
                signal_type=SignalType.EXIT,
                related_order_id="scalp_entry_123",
                strategy="scalping"
            )
            
            exit_result = await signal_processor.process_signal(exit_signal)
            assert exit_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_multi_asset_portfolio_workflow(self, signal_processor):
        """Test managing positions across multiple assets."""
        assets = ["EURUSD", "GBPUSD", "USDJPY"]
        signals = []
        
        for asset in assets:
            signal = SignalRequest(
                broker=BrokerType.MT4,
                symbol=asset,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=0.1,
                signal_type=SignalType.ENTRY
            )
            signals.append(signal)
        
        with patch('app.brokers.mt4_executor.MT4Executor') as mock_broker:
            mock_executor = AsyncMock()
            mock_broker.return_value = mock_executor
            
            # Mock successful executions for all assets
            def mock_place_order(signal):
                mock_trade = Mock()
                mock_trade.order_id = f"portfolio_{signal.symbol}_123"
                mock_trade.status = "filled"
                return mock_trade
            
            mock_executor.place_order.side_effect = mock_place_order
            
            # Process all portfolio signals
            tasks = [signal_processor.process_signal(signal) for signal in signals]
            results = await asyncio.gather(*tasks)
            
            # Verify all assets were processed
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result["success"] is True
                assert assets[i] in result["order_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])