import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.domain.services.account_routing_service import AccountRoutingService
from app.models.database_models import (
    TradingAccount,
    WebhookConfig,
    BrokerType,
    AccountType,
)


@pytest.fixture
def routing_session():
    """Provide a fresh SQLite session for routing tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_account(session, user_id: int, account_number: str, webhook_key: str) -> TradingAccount:
    """Create an active signal-enabled trading account."""
    account = TradingAccount(
        user_id=user_id,
        broker=BrokerType.MT4,
        account_type=AccountType.DEMO,
        account_number=account_number,
        account_name=f"Test Account {account_number}",
        webhook_key=webhook_key,
        is_active=True,
        is_signal_enabled=True,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_specific_accounts_routing_returns_all_targets(routing_session):
    """specific_accounts routing should return the listed accounts."""
    user_id = 42
    acc_a = create_account(routing_session, user_id, "ACC-A", str(uuid.uuid4()))
    acc_b = create_account(routing_session, user_id, "ACC-B", str(uuid.uuid4()))

    config = WebhookConfig(
        user_id=user_id,
        name="multi-account-route",
        webhook_key="multi-specific",
        source="tradingview",
        routing_strategy="specific_accounts",
        specific_account_ids=[acc_a.id, acc_b.id],
        is_active=True,
    )
    routing_session.add(config)
    routing_session.commit()

    routing_service = AccountRoutingService(routing_session)
    decision = routing_service.resolve_accounts(
        webhook_key=config.webhook_key,
        symbol="EURUSD",
        strategy_id="strategy-1",
        action="buy",
    )

    assert decision.is_valid
    assert decision.strategy_used == "specific_accounts"
    assert {acct.id for acct in decision.accounts} == {acc_a.id, acc_b.id}
    assert decision.user_id == user_id


def test_rules_based_routing_matches_symbol(routing_session):
    """rules_based routing should select accounts that match the symbol filter."""
    user_id = 7
    acc_match = create_account(routing_session, user_id, "ACC-MATCH", str(uuid.uuid4()))
    create_account(routing_session, user_id, "ACC-OTHER", str(uuid.uuid4()))

    config = WebhookConfig(
        user_id=user_id,
        name="rules-route",
        webhook_key="rules-based",
        source="tradingview",
        routing_strategy="rules_based",
        routing_rules=[
            {
                "name": "match-eurusd",
                "symbols": ["EURUSD"],
                "account_ids": [acc_match.id],
                "priority": 10,
            }
        ],
        is_active=True,
    )
    routing_session.add(config)
    routing_session.commit()

    routing_service = AccountRoutingService(routing_session)
    decision = routing_service.resolve_accounts(
        webhook_key=config.webhook_key,
        symbol="EURUSD",
        strategy_id="any",
        action="buy",
    )

    assert decision.is_valid
    assert decision.strategy_used == "rules_based"
    assert len(decision.accounts) == 1
    assert decision.accounts[0].id == acc_match.id


def test_rules_based_routing_falls_back_to_default(routing_session):
    """When no rules match, fallback to the default account."""
    user_id = 13
    default_account = create_account(routing_session, user_id, "ACC-DEFAULT", str(uuid.uuid4()))

    config = WebhookConfig(
        user_id=user_id,
        name="rules-fallback",
        webhook_key="rules-fallback",
        source="tradingview",
        routing_strategy="rules_based",
        default_account_id=default_account.id,
        routing_rules=[
            {
                "name": "never-match",
                "symbols": ["NOMATCH"],
                "account_ids": [default_account.id],
                "priority": 1,
            }
        ],
        is_active=True,
    )
    routing_session.add(config)
    routing_session.commit()

    routing_service = AccountRoutingService(routing_session)
    decision = routing_service.resolve_accounts(
        webhook_key=config.webhook_key,
        symbol="EURUSD",
        strategy_id="any",
        action="buy",
    )

    assert decision.is_valid
    assert decision.strategy_used == "default_only"
    assert len(decision.accounts) == 1
    assert decision.accounts[0].id == default_account.id
