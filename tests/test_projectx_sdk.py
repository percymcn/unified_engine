"""
Tests for ProjectX SDK integration.

Tests the ProjectXSDKService wrapper and ProjectXExecutor dual-mode functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestProjectXSDKService:
    """Tests for ProjectXSDKService."""

    @pytest.fixture
    def mock_projectx(self):
        """Mock ProjectX client."""
        with patch('app.services.projectx_sdk_service.ProjectX') as mock:
            client = MagicMock()
            client.authenticate = AsyncMock()
            client.account_info = MagicMock(
                id="test-123",
                name="Test Account",
                balance=50000.0,
                equity=50000.0,
                margin=0.0,
                free_margin=50000.0,
                currency="USD",
            )
            client.search_instruments = AsyncMock(return_value=[
                MagicMock(id="1", name="MNQ", description="Micro NASDAQ")
            ])
            client.get_bars = AsyncMock(return_value=[])
            mock.return_value = client
            yield mock, client

    @pytest.fixture
    def mock_trading_suite(self):
        """Mock TradingSuite."""
        with patch('app.services.projectx_sdk_service.TradingSuite') as mock:
            suite = MagicMock()
            suite.instrument_id = "MNQ-123"
            suite.orders = MagicMock()
            suite.orders.place_market_order = AsyncMock(return_value=MagicMock(
                success=True,
                orderId="order-123"
            ))
            suite.orders.place_limit_order = AsyncMock(return_value=MagicMock(
                success=True,
                orderId="order-456"
            ))
            suite.positions = MagicMock()
            suite.positions.get_all_positions = AsyncMock(return_value=[])
            suite.disconnect = AsyncMock()
            mock.create = AsyncMock(return_value=suite)
            yield mock, suite

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_projectx):
        """Test successful connection."""
        mock_class, mock_client = mock_projectx

        # Also mock SDK_AVAILABLE
        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )

            result = await service.connect()

            assert result is True
            assert service.is_connected is True
            mock_client.authenticate.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_projectx):
        """Test connection failure."""
        mock_class, mock_client = mock_projectx
        mock_client.authenticate.side_effect = Exception("Auth failed")

        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )

            result = await service.connect()

            assert result is False
            assert service.is_connected is False

    @pytest.mark.asyncio
    async def test_get_account_info(self, mock_projectx):
        """Test getting account info."""
        mock_class, mock_client = mock_projectx

        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )
            await service.connect()

            info = await service.get_account_info()

            assert info["name"] == "Test Account"
            assert info["balance"] == 50000.0

    @pytest.mark.asyncio
    async def test_place_market_order(self, mock_projectx, mock_trading_suite):
        """Test placing market order."""
        mock_class, mock_client = mock_projectx
        mock_suite_class, mock_suite = mock_trading_suite

        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )
            await service.connect()

            result = await service.place_market_order(
                instrument="MNQ",
                side="buy",
                size=1
            )

            assert result["success"] is True
            assert result["order_id"] == "order-123"
            mock_suite.orders.place_market_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_limit_order(self, mock_projectx, mock_trading_suite):
        """Test placing limit order."""
        mock_class, mock_client = mock_projectx
        mock_suite_class, mock_suite = mock_trading_suite

        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )
            await service.connect()

            result = await service.place_limit_order(
                instrument="MNQ",
                side="sell",
                size=2,
                limit_price=21050.0
            )

            assert result["success"] is True
            assert result["order_id"] == "order-456"

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_projectx, mock_trading_suite):
        """Test disconnection."""
        mock_class, mock_client = mock_projectx

        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )
            await service.connect()

            await service.disconnect()

            assert service.is_connected is False

    @pytest.mark.asyncio
    async def test_search_instruments(self, mock_projectx):
        """Test searching for instruments."""
        mock_class, mock_client = mock_projectx

        with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
            from app.services.projectx_sdk_service import ProjectXSDKService

            service = ProjectXSDKService(
                username="test_user",
                api_key="test_key"
            )
            await service.connect()

            instruments = await service.search_instruments("MNQ")

            assert len(instruments) == 1
            assert instruments[0]["symbol"] == "MNQ"
            mock_client.search_instruments.assert_called_with("MNQ")


class TestProjectXExecutorSDKMode:
    """Tests for ProjectXExecutor in SDK mode."""

    @pytest.fixture
    def mock_sdk_service(self):
        """Mock SDK service."""
        with patch('app.brokers.projectx_executor.ProjectXSDKService') as mock:
            service = MagicMock()
            service.connect = AsyncMock(return_value=True)
            service.disconnect = AsyncMock()
            service.is_connected = True
            service.get_account_info = AsyncMock(return_value={
                "id": "acc-123",
                "name": "Test",
                "balance": 50000.0,
                "equity": 50000.0,
                "margin": 0.0,
                "free_margin": 50000.0,
                "currency": "USD"
            })
            service.get_positions = AsyncMock(return_value=[])
            service.place_market_order = AsyncMock(return_value={
                "success": True,
                "order_id": "order-123",
                "status": "submitted"
            })
            mock.return_value = service
            yield mock, service

    @pytest.mark.asyncio
    async def test_executor_sdk_mode_init(self, mock_sdk_service):
        """Test executor initializes in SDK mode."""
        mock_class, mock_service = mock_sdk_service

        with patch('app.brokers.projectx_executor.SDK_AVAILABLE', True):
            from app.brokers.projectx_executor import ProjectXExecutor

            executor = ProjectXExecutor(
                username="test",
                api_key="key123"
            )

            result = await executor.initialize()

            assert result is True
            assert executor.is_using_sdk is True

    @pytest.mark.asyncio
    async def test_executor_get_accounts_sdk(self, mock_sdk_service):
        """Test getting accounts via SDK."""
        mock_class, mock_service = mock_sdk_service

        with patch('app.brokers.projectx_executor.SDK_AVAILABLE', True):
            from app.brokers.projectx_executor import ProjectXExecutor

            executor = ProjectXExecutor(
                username="test",
                api_key="key123"
            )
            await executor.initialize()

            accounts = await executor.get_accounts()

            assert len(accounts) == 1
            assert accounts[0].balance == 50000.0
            mock_service.get_account_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_executor_fallback_to_httpx(self, mock_sdk_service):
        """Test executor falls back to httpx on SDK failure."""
        mock_class, mock_service = mock_sdk_service
        mock_service.connect = AsyncMock(return_value=False)

        with patch('app.brokers.projectx_executor.SDK_AVAILABLE', True):
            with patch('httpx.AsyncClient') as mock_httpx:
                mock_client = MagicMock()
                mock_response = MagicMock(
                    status_code=200,
                    text="jwt-token-here",
                    headers={"content-type": "text/plain"}
                )
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.headers = {}
                mock_httpx.return_value = mock_client

                from app.brokers.projectx_executor import ProjectXExecutor

                executor = ProjectXExecutor(
                    username="test",
                    api_key="key123"
                )

                result = await executor.initialize()

                # Should fall back to httpx
                assert result is True
                assert executor.is_using_sdk is False

    @pytest.mark.asyncio
    async def test_executor_disconnect(self, mock_sdk_service):
        """Test executor disconnect."""
        mock_class, mock_service = mock_sdk_service

        with patch('app.brokers.projectx_executor.SDK_AVAILABLE', True):
            from app.brokers.projectx_executor import ProjectXExecutor

            executor = ProjectXExecutor(
                username="test",
                api_key="key123"
            )
            await executor.initialize()

            await executor.disconnect()

            mock_service.disconnect.assert_called_once()


class TestTopstepAdapter:
    """Tests for TopstepAdapter with credential parameters."""

    @pytest.mark.asyncio
    async def test_adapter_passes_credentials(self):
        """Test adapter passes credentials to executor."""
        with patch('app.infrastructure.adapters.topstep_adapter.ProjectXExecutor') as mock_executor:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.is_connected = True
            mock_executor.return_value = mock_instance

            from app.infrastructure.adapters.topstep_adapter import TopstepAdapter

            adapter = TopstepAdapter(
                account_id="acc-123",
                username="test_user",
                api_key="test_key"
            )

            await adapter.connect()

            # Verify executor was created with credentials
            mock_executor.assert_called_once_with(
                account_id="acc-123",
                username="test_user",
                api_key="test_key",
            )

    @pytest.mark.asyncio
    async def test_adapter_uses_provided_executor(self):
        """Test adapter uses provided executor."""
        mock_executor = MagicMock()
        mock_executor.initialize = AsyncMock(return_value=True)
        mock_executor.is_connected = True

        from app.infrastructure.adapters.topstep_adapter import TopstepAdapter

        adapter = TopstepAdapter(executor=mock_executor)

        await adapter.connect()

        # Should use provided executor, not create new one
        mock_executor.initialize.assert_called_once()


class TestFuturesRollover:
    """Tests for futures contract handling."""

    @pytest.mark.asyncio
    async def test_contract_search(self):
        """Test searching for contracts via SDK."""
        with patch('app.services.projectx_sdk_service.ProjectX') as mock_projectx:
            mock_client = MagicMock()
            mock_client.authenticate = AsyncMock()
            mock_client.account_info = MagicMock(
                id="test-123",
                name="Test Account",
                balance=50000.0,
            )
            mock_client.search_instruments = AsyncMock(return_value=[
                MagicMock(id="1", name="MNQH25", description="Micro NASDAQ Mar 25"),
                MagicMock(id="2", name="MNQM25", description="Micro NASDAQ Jun 25"),
            ])
            mock_projectx.return_value = mock_client

            with patch('app.services.projectx_sdk_service.SDK_AVAILABLE', True):
                from app.services.projectx_sdk_service import ProjectXSDKService

                service = ProjectXSDKService(
                    username="test_user",
                    api_key="test_key"
                )
                await service.connect()

                instruments = await service.search_instruments("MNQ")

                assert len(instruments) == 2
                # SDK handles futures rollover by returning active contracts
                mock_client.search_instruments.assert_called_with("MNQ")
