"""Mini-deploy checks: TrailHacker source coercion and dual tier ids.

These tests do not touch brokers, place orders, or delete data.
"""
from app.domain.enums import (
    SignalSource,
    coerce_signal_source,
    is_empty_signal_payload,
)
from app.core.billing import (
    get_tier_limits,
    is_enterprise_tier,
    is_free_tier,
    normalize_tier_id,
    tier_level,
)
from app.services.telegram_service import user_has_tier_access
from app.services.webhook_retention_service import get_retention_days
from app.models.models import SignalSource as OrmSignalSource
from app.infrastructure.mappers.signal_mapper import SignalMapper
from app.domain.entities.signal import Signal
from app.domain.enums import SignalAction
from app.domain.value_objects import SignalId, Symbol, Volume
from decimal import Decimal


class TestSignalSourceCoercion:
    def test_trailhacker_maps_to_existing_enum(self):
        source = coerce_signal_source("trailhacker")
        assert source is SignalSource.TRAILHACKER
        assert source.value == "trailhacker"
        assert source is not SignalSource.CUSTOM

    def test_custom_and_unknown_do_not_persist_custom(self):
        for raw in ("CUSTOM", "custom", "unknown", "", None):
            source = coerce_signal_source(raw)
            assert source is not SignalSource.CUSTOM
            assert source.value != "custom"
            assert source.value in {"tradingview", "trailhacker", "manual", "api"}

    def test_tradingview_is_unchanged(self):
        assert coerce_signal_source("tradingview") is SignalSource.TRADINGVIEW
        assert coerce_signal_source("TRADINGVIEW") is SignalSource.TRADINGVIEW
        assert coerce_signal_source(SignalSource.TRADINGVIEW) is SignalSource.TRADINGVIEW

    def test_empty_payload_is_a_test_ping(self):
        assert is_empty_signal_payload(None) is True
        assert is_empty_signal_payload({}) is True
        assert is_empty_signal_payload({"test": True}) is True
        assert is_empty_signal_payload({"symbol": "ES", "signal": "buy"}) is False
        assert is_empty_signal_payload({"ticker": "ES", "action": "sell"}) is False

    def test_mapper_persists_orm_member_not_custom(self):
        entity = Signal(
            id=SignalId("11111111-1111-1111-1111-111111111111"),
            source=SignalSource.CUSTOM,
            symbol=Symbol("ES"),
            action=SignalAction.BUY,
            volume=Volume(Decimal("1")),
        )
        model = SignalMapper.to_model(entity)
        assert model.source == OrmSignalSource.API
        assert model.source != OrmSignalSource.CUSTOM
        assert getattr(model.source, "name", "") != "CUSTOM"

    def test_mapper_persists_trailhacker(self):
        entity = Signal(
            id=SignalId("22222222-2222-2222-2222-222222222222"),
            source=coerce_signal_source("TrailHacker"),
            symbol=Symbol("NQ"),
            action=SignalAction.SELL,
            volume=Volume(Decimal("1")),
        )
        model = SignalMapper.to_model(entity)
        assert model.source == OrmSignalSource.TRAILHACKER


class TestDualTierIds:
    def test_enterprise_and_tier_4_are_the_same_rank(self):
        assert normalize_tier_id("enterprise") == "tier_4"
        assert normalize_tier_id("TIER_4") == "tier_4"
        assert normalize_tier_id("tier-4") == "tier_4"
        assert is_enterprise_tier("enterprise") is True
        assert is_enterprise_tier("tier_4") is True
        assert tier_level("enterprise") == tier_level("tier_4") == 4

    def test_free_gate_stays_closed_for_blank_and_unknown(self):
        assert is_free_tier(None) is True
        assert is_free_tier("") is True
        assert is_free_tier("not-a-plan") is True
        assert tier_level("free") == 0
        assert is_enterprise_tier("free") is False

    def test_enterprise_alias_is_not_treated_as_free_for_access(self):
        assert user_has_tier_access("tier_4", "enterprise") is True
        assert user_has_tier_access("enterprise", "tier_4") is True
        assert user_has_tier_access("free", "pro") is False
        assert user_has_tier_access("tier_4", "free") is True

    def test_webhook_log_retention_matches_for_both_enterprise_ids(self):
        assert get_retention_days("enterprise") == get_retention_days("tier_4")
        assert get_retention_days("enterprise") == 90
        assert get_retention_days("free") == 7
        assert get_retention_days("nope") == 7

    def test_known_tier_rows_are_not_collapsed_to_free_limits(self):
        enterprise = get_tier_limits("Enterprise")
        tier_4 = get_tier_limits("tier_4")
        free = get_tier_limits("free")
        assert enterprise.max_webhooks == -1
        assert tier_4.max_webhooks == -1
        assert free.max_webhooks == 1
        assert enterprise.tier == "enterprise"
        assert tier_4.tier == "tier_4"
