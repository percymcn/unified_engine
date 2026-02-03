import pytest

from app.brokers import projectx_executor
from app.brokers.projectx_executor import ProjectXExecutor


@pytest.mark.asyncio
async def test_projectx_executor_uses_account_name_for_sdk_scope(monkeypatch):
    created = {}

    class DummyProjectXSDKService:
        def __init__(self, username, api_key, account_name=None):
            created["username"] = username
            created["api_key"] = api_key
            created["account_name"] = account_name
            self.is_connected = False

        async def connect(self):
            self.is_connected = True
            return True

        async def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr(projectx_executor, "SDK_AVAILABLE", True)
    monkeypatch.setattr(projectx_executor, "ProjectXSDKService", DummyProjectXSDKService)

    executor = ProjectXExecutor(
        account_id="ACC-123",
        account_name="ProjectX Account A",
        username="user@example.com",
        api_key="api-key"
    )

    assert await executor.initialize() is True
    assert created["account_name"] == "ProjectX Account A"
