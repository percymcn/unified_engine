"""Unit tests for broken product-surface fixes."""

from types import SimpleNamespace

import pytest

from app.core.broker_health import broker_is_connected, build_unified_health
from app.core.entitlements import canonical_tier_id, legacy_subscription_tier
from app.core.signal_sources import is_empty_trailhacker_payload, resolve_signal_source
from app.domain.enums import SignalSource
from app.services.account_balance import (
    account_identity_matches,
    apply_discovered_balances,
    balance_for_nested_account,
    delete_trading_account,
    resolve_card_balances,
)
from app.services.ai_analysis import build_full_analysis
from app.services.market_scans import run_gap_analyze, run_low_float_scan, run_premarket_generate
from app.services.ops_status import (
    build_api_keys_payload,
    build_daily_summary,
    build_errors_payload,
    empty_daily_summary,
)


def test_trailhacker_aliases_map_to_valid_enum():
    assert resolve_signal_source("TrailHacker") is SignalSource.TRAILHACKER
    assert resolve_signal_source("trail-hacker") is SignalSource.TRAILHACKER
    assert resolve_signal_source("custom") is SignalSource.API
    assert resolve_signal_source("CUSTOM") is SignalSource.API
    assert "custom" not in {item.value for item in SignalSource}


def test_empty_trailhacker_payload_is_rejected():
    assert is_empty_trailhacker_payload({}) is True
    assert is_empty_trailhacker_payload({"symbol": "UNKNOWN"}) is True
    assert is_empty_trailhacker_payload({"symbol": "MES"}) is True
    assert is_empty_trailhacker_payload({"symbol": "MES", "signal": "buy"}) is False


def test_tier_aliases_share_limits():
    assert canonical_tier_id("enterprise") == "tier_4"
    assert canonical_tier_id("tier_4") == "tier_4"
    assert canonical_tier_id("basic") == "free"
    assert canonical_tier_id("free") == "free"
    assert canonical_tier_id("premium") == "tier_3"
    assert legacy_subscription_tier("tier_4") == "enterprise"
    assert legacy_subscription_tier("basic") == "free"
    assert legacy_subscription_tier("tier_2") == "premium"

    from app.core.billing import get_tier_limits

    enterprise = get_tier_limits("enterprise")
    tier_4 = get_tier_limits("tier_4")
    basic = get_tier_limits("basic")
    assert enterprise.max_broker_connections == tier_4.max_broker_connections == 4
    assert basic.max_broker_connections == get_tier_limits("free").max_broker_connections


def test_broker_is_connected_handles_method_and_bool():
    class MethodBroker:
        def is_connected(self):
            return False

    class FlagBroker:
        is_connected = False
        _connected_flag = True

    class RaisingBroker:
        def is_connected(self):
            raise RuntimeError("down")

    assert broker_is_connected(MethodBroker()) is False
    assert broker_is_connected(FlagBroker()) is True
    assert broker_is_connected(RaisingBroker()) is False

    payload = build_unified_health({"tl": MethodBroker(), "tv": RaisingBroker()})
    assert payload["status"] == "degraded"
    assert payload["version"]
    assert payload["services"]["api"] == "up"
    assert payload["brokers"]["tl"]["connected"] is False


def test_nested_balance_is_not_copied_onto_every_account():
    state = {"balance": 10, "equity": 10, "currency": "USD"}
    selected_balance, _, _ = balance_for_nested_account({}, state, "1", "1")
    other_balance, _, _ = balance_for_nested_account(
        {"balance": 25000, "equity": 25100},
        state,
        "2",
        "1",
    )
    assert selected_balance == 10
    assert other_balance == 25000


def test_card_uses_selected_subaccount_when_stored_balance_is_zero():
    balance, equity = resolve_card_balances(
        0,
        0,
        {
            "selected_subaccount": {"id": "demo-1", "balance": 1500, "equity": 1600},
            "discovered_accounts": [{"id": "other", "balance": 9}],
        },
    )
    assert balance == 1500
    assert equity == 1600

    kept, _ = resolve_card_balances(
        80,
        80,
        {"selected_subaccount": {"balance": 1500, "equity": 1600}},
    )
    assert kept == 80


def test_delete_trading_account_commits():
    row = SimpleNamespace(id=7, account_number="MES-1", user_id=3)

    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return [row]

    class DB:
        def __init__(self):
            self.deleted = None
            self.committed = False

        def query(self, _model):
            return Query()

        def delete(self, target):
            self.deleted = target

        def commit(self):
            self.committed = True

    db = DB()
    assert delete_trading_account(db, 3, "MES-1") is True
    assert db.deleted is row
    assert db.committed is True
    assert account_identity_matches("7", 7, "other") is True


def test_discovered_balances_fill_zero_stored_rows():
    stored = SimpleNamespace(balance=0, equity=0, extra_metadata=None)
    updated = apply_discovered_balances(
        [stored],
        [{"id": "demo", "balance": 4200, "equity": 4300}],
    )
    assert updated == 1
    assert stored.balance == 4200
    assert stored.extra_metadata["discovered_accounts"][0]["id"] == "demo"


def test_market_scans_compute_supplied_symbols_and_empty_provider():
    empty = run_premarket_generate({})
    assert empty["results"] == []
    assert empty["status"] == "ok"
    assert "no market data provider" in empty["message"]

    gaps = run_gap_analyze(
        {"symbols": [{"symbol": "AAPL", "previous_close": 100, "open_price": 110}]}
    )
    assert gaps["results"][0]["gap_percent"] == pytest.approx(10.0)

    floats = run_low_float_scan(
        {"symbols": [{"symbol": "TINY", "float_shares": 1_000_000}, {"symbol": "BIG", "float_shares": 50_000_000}]}
    )
    assert [row["symbol"] for row in floats["results"]] == ["TINY"]


def test_full_analysis_returns_neutral_composite():
    result = build_full_analysis("mes", ["technical", "risk"])
    assert result["ticker"] == "MES"
    assert result["analyses"]["technical"]["summary"]
    assert result["analyses"]["technical"]["recommendation"] == "neutral"
    assert result["composite"]["composite_recommendation"] == "neutral"
    assert result["composite"]["composite_confidence"] == 0


def test_ops_payloads_do_not_invent_trades_or_keys():
    daily = build_daily_summary([SimpleNamespace(profit=12.5), SimpleNamespace(profit=-2.5)], "2026-09-14")
    assert daily["summary"]["total_trades"] == 2
    assert daily["summary"]["total_pnl"] == pytest.approx(10.0)
    assert daily["source"] == "trades"

    empty = empty_daily_summary("2026-09-14")
    assert empty["summary"]["total_pnl"] == 0
    assert empty["summary"]["total_trades"] == 0
    assert empty["source"] == "unavailable"

    errors = build_errors_payload(
        [SimpleNamespace(error_message="SDK not initialized", source="trailhacker", created_at=None)]
    )
    assert errors["errors"][0]["message"] == "SDK not initialized"
    assert "1250.50" not in str(errors)

    keys = build_api_keys_payload([SimpleNamespace(id=1, name="desk", is_active=True, last_used_at=None, expires_at=None)])
    assert "key_hash" not in keys["api_keys"][0]
    assert keys["api_keys"][0]["name"] == "desk"
