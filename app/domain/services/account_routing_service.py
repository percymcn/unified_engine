"""
Account Routing Service

Handles multi-account routing logic for webhook signals.
Supports: all_accounts, specific_accounts, rules_based, default_only strategies.
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.database_models import TradingAccount, WebhookConfig

logger = logging.getLogger(__name__)


class RoutingDecision:
    """Result of routing decision"""
    def __init__(
        self,
        accounts: List[TradingAccount],
        user_id: int,
        strategy_used: str,
        reason: str,
        webhook_config: Optional[WebhookConfig] = None
    ):
        self.accounts = accounts
        self.user_id = user_id
        self.strategy_used = strategy_used
        self.reason = reason
        self.webhook_config = webhook_config

    @property
    def is_valid(self) -> bool:
        return len(self.accounts) > 0


class AccountRoutingService:
    """
    Service for resolving webhook signals to target trading accounts.

    Routing Priority:
    1. Account-level webhook_key (direct account match)
    2. WebhookConfig routing_strategy:
       - all_accounts: All user's signal-enabled accounts
       - specific_accounts: Only accounts in specific_account_ids
       - rules_based: Apply routing_rules by symbol/strategy
       - default_only: Only the default_account_id
    """

    def __init__(self, db: Session):
        self.db = db

    def resolve_accounts(
        self,
        webhook_key: str,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        action: Optional[str] = None
    ) -> RoutingDecision:
        """
        Resolve webhook_key to target trading account(s).

        Args:
            webhook_key: The webhook key from the signal
            symbol: Trading symbol (for rules_based routing)
            strategy_id: Strategy identifier (for rules_based routing)
            action: Trade action (buy/sell/close)

        Returns:
            RoutingDecision with target accounts and metadata
        """
        # First: Try direct account-level webhook_key match
        account = self.db.query(TradingAccount).filter(
            TradingAccount.webhook_key == webhook_key,
            TradingAccount.is_active == True
        ).first()

        if account:
            logger.info(f"Direct account match for webhook_key: account_id={account.id}")
            return RoutingDecision(
                accounts=[account],
                user_id=account.user_id,
                strategy_used="direct_account_key",
                reason="Matched account-level webhook_key"
            )

        # Second: Try WebhookConfig match
        webhook_config = self.db.query(WebhookConfig).filter(
            WebhookConfig.webhook_key == webhook_key,
            WebhookConfig.is_active == True
        ).first()

        if not webhook_config:
            logger.warning(f"No webhook_config found for key: {webhook_key[:12]}...")
            return RoutingDecision(
                accounts=[],
                user_id=0,
                strategy_used="none",
                reason="Invalid webhook_key - no matching config"
            )

        # Apply routing strategy
        routing_strategy = webhook_config.routing_strategy or "default_only"
        user_id = webhook_config.user_id

        logger.info(f"Applying routing strategy: {routing_strategy} for user_id={user_id}")

        if routing_strategy == "all_accounts":
            return self._route_all_accounts(webhook_config, symbol, action)

        elif routing_strategy == "specific_accounts":
            return self._route_specific_accounts(webhook_config, symbol, action)

        elif routing_strategy == "rules_based":
            return self._route_rules_based(webhook_config, symbol, strategy_id, action)

        else:  # default_only
            return self._route_default_only(webhook_config)

    def _route_all_accounts(
        self,
        config: WebhookConfig,
        symbol: Optional[str],
        action: Optional[str]
    ) -> RoutingDecision:
        """Route to all signal-enabled accounts for the user"""
        query = self.db.query(TradingAccount).filter(
            TradingAccount.user_id == config.user_id,
            TradingAccount.is_active == True,
            TradingAccount.is_signal_enabled == True
        )

        # Apply symbol filter if configured
        if config.symbol_filter and symbol:
            # symbol_filter is a list of allowed symbols or patterns
            if not self._matches_symbol_filter(symbol, config.symbol_filter):
                return RoutingDecision(
                    accounts=[],
                    user_id=config.user_id,
                    strategy_used="all_accounts",
                    reason=f"Symbol {symbol} not in allowed list",
                    webhook_config=config
                )

        # Apply action filter if configured
        if config.action_filter and action:
            if action.lower() not in [a.lower() for a in config.action_filter]:
                return RoutingDecision(
                    accounts=[],
                    user_id=config.user_id,
                    strategy_used="all_accounts",
                    reason=f"Action {action} not in allowed list",
                    webhook_config=config
                )

        accounts = query.order_by(TradingAccount.signal_priority.desc()).all()

        return RoutingDecision(
            accounts=accounts,
            user_id=config.user_id,
            strategy_used="all_accounts",
            reason=f"Routing to all {len(accounts)} signal-enabled accounts",
            webhook_config=config
        )

    def _route_specific_accounts(
        self,
        config: WebhookConfig,
        symbol: Optional[str],
        action: Optional[str]
    ) -> RoutingDecision:
        """Route to specific accounts defined in config"""
        account_ids = config.specific_account_ids or []

        if not account_ids:
            # Fallback to default account
            return self._route_default_only(config)

        accounts = self.db.query(TradingAccount).filter(
            TradingAccount.id.in_(account_ids),
            TradingAccount.user_id == config.user_id,
            TradingAccount.is_active == True
        ).order_by(TradingAccount.signal_priority.desc()).all()

        return RoutingDecision(
            accounts=accounts,
            user_id=config.user_id,
            strategy_used="specific_accounts",
            reason=f"Routing to {len(accounts)} specific accounts",
            webhook_config=config
        )

    def _route_rules_based(
        self,
        config: WebhookConfig,
        symbol: Optional[str],
        strategy_id: Optional[str],
        action: Optional[str]
    ) -> RoutingDecision:
        """Route based on symbol/strategy rules"""
        rules = config.routing_rules or []
        matched_account_ids = set()
        match_reasons = []

        for rule in rules:
            if self._rule_matches(rule, symbol, strategy_id, action):
                rule_accounts = rule.get("account_ids", [])
                matched_account_ids.update(rule_accounts)
                match_reasons.append(rule.get("name", "unnamed_rule"))

        if not matched_account_ids:
            # No rules matched - fallback to default
            logger.info("No routing rules matched, falling back to default")
            return self._route_default_only(config)

        accounts = self.db.query(TradingAccount).filter(
            TradingAccount.id.in_(list(matched_account_ids)),
            TradingAccount.user_id == config.user_id,
            TradingAccount.is_active == True
        ).order_by(TradingAccount.signal_priority.desc()).all()

        return RoutingDecision(
            accounts=accounts,
            user_id=config.user_id,
            strategy_used="rules_based",
            reason=f"Matched rules: {', '.join(match_reasons)}",
            webhook_config=config
        )

    def _route_default_only(self, config: WebhookConfig) -> RoutingDecision:
        """Route to default account only"""
        account = None

        if config.default_account_id:
            account = self.db.query(TradingAccount).filter(
                TradingAccount.id == config.default_account_id,
                TradingAccount.user_id == config.user_id,
                TradingAccount.is_active == True
            ).first()

        if not account:
            # Fallback: get most recently updated signal-enabled account
            account = self.db.query(TradingAccount).filter(
                TradingAccount.user_id == config.user_id,
                TradingAccount.is_active == True,
                TradingAccount.is_signal_enabled == True
            ).order_by(TradingAccount.updated_at.desc()).first()

        accounts = [account] if account else []

        return RoutingDecision(
            accounts=accounts,
            user_id=config.user_id,
            strategy_used="default_only",
            reason="Routing to default account" if account else "No default account found",
            webhook_config=config
        )

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        symbol: Optional[str],
        strategy_id: Optional[str],
        action: Optional[str]
    ) -> bool:
        """Check if a routing rule matches the signal"""
        # Check symbol match
        rule_symbols = rule.get("symbols", [])
        if rule_symbols and symbol:
            symbol_upper = symbol.upper()
            matched = False
            for pattern in rule_symbols:
                pattern_upper = pattern.upper()
                # Support wildcard patterns
                if pattern_upper == "*":
                    matched = True
                    break
                elif pattern_upper.endswith("*"):
                    if symbol_upper.startswith(pattern_upper[:-1]):
                        matched = True
                        break
                elif symbol_upper == pattern_upper:
                    matched = True
                    break
            if not matched:
                return False

        # Check strategy match
        rule_strategies = rule.get("strategies", [])
        if rule_strategies and strategy_id:
            if strategy_id not in rule_strategies and "*" not in rule_strategies:
                return False

        # Check action match
        rule_actions = rule.get("actions", [])
        if rule_actions and action:
            if action.lower() not in [a.lower() for a in rule_actions]:
                return False

        return True

    def _matches_symbol_filter(self, symbol: str, filter_list: List[str]) -> bool:
        """Check if symbol matches filter list (supports wildcards)"""
        symbol_upper = symbol.upper()
        for pattern in filter_list:
            pattern_upper = pattern.upper()
            if pattern_upper == "*":
                return True
            elif pattern_upper.endswith("*"):
                if symbol_upper.startswith(pattern_upper[:-1]):
                    return True
            elif symbol_upper == pattern_upper:
                return True
        return False
