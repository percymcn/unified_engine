"""
Signal Routing Service - Domain Service

Provides flexible signal routing to accounts based on configurable strategies:
- ALL_ACCOUNTS: Route to all active, signal-enabled accounts
- SPECIFIC_ACCOUNTS: Route to explicitly listed account IDs
- RULES_BASED: Evaluate routing rules against signal data
- DEFAULT_ONLY: Route only to the default account

Supports rule-based routing with conditions on symbol, action, source, etc.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Signal routing strategy options"""
    ALL_ACCOUNTS = "all_accounts"           # Route to all active accounts
    SPECIFIC_ACCOUNTS = "specific_accounts"  # Route to listed account IDs
    RULES_BASED = "rules_based"              # Evaluate routing rules
    DEFAULT_ONLY = "default_only"            # Only default account


class RoutingOperator(str, Enum):
    """Operators for routing rule conditions"""
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN_LIST = "in"
    NOT_IN_LIST = "not_in"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"
    REGEX = "regex"


@dataclass
class RoutingCondition:
    """A single condition within a routing rule"""
    field: str              # "symbol", "action", "source", "strategy_name"
    operator: RoutingOperator
    value: Any              # Comparison value

    def matches(self, signal_data: Dict[str, Any]) -> bool:
        """Check if this condition matches the signal data"""
        field_value = signal_data.get(self.field)
        if field_value is None:
            return False

        return self._evaluate(field_value, self.operator, self.value)

    def _evaluate(self, field_value: Any, op: RoutingOperator, compare_value: Any) -> bool:
        """Evaluate the condition"""
        try:
            if op == RoutingOperator.EQUALS:
                return str(field_value).lower() == str(compare_value).lower()
            elif op == RoutingOperator.NOT_EQUALS:
                return str(field_value).lower() != str(compare_value).lower()
            elif op == RoutingOperator.CONTAINS:
                return str(compare_value).lower() in str(field_value).lower()
            elif op == RoutingOperator.STARTS_WITH:
                return str(field_value).lower().startswith(str(compare_value).lower())
            elif op == RoutingOperator.ENDS_WITH:
                return str(field_value).lower().endswith(str(compare_value).lower())
            elif op == RoutingOperator.IN_LIST:
                if isinstance(compare_value, list):
                    return str(field_value).lower() in [str(v).lower() for v in compare_value]
                return str(field_value).lower() == str(compare_value).lower()
            elif op == RoutingOperator.NOT_IN_LIST:
                if isinstance(compare_value, list):
                    return str(field_value).lower() not in [str(v).lower() for v in compare_value]
                return str(field_value).lower() != str(compare_value).lower()
            elif op == RoutingOperator.GREATER_THAN:
                return float(field_value) > float(compare_value)
            elif op == RoutingOperator.LESS_THAN:
                return float(field_value) < float(compare_value)
            elif op == RoutingOperator.GREATER_OR_EQUAL:
                return float(field_value) >= float(compare_value)
            elif op == RoutingOperator.LESS_OR_EQUAL:
                return float(field_value) <= float(compare_value)
            elif op == RoutingOperator.REGEX:
                import re
                pattern = re.compile(str(compare_value), re.IGNORECASE)
                return bool(pattern.search(str(field_value)))
        except (ValueError, TypeError) as e:
            logger.warning(f"Error evaluating condition: {e}")
            return False

        return False


@dataclass
class RoutingRule:
    """A single routing rule with condition and target accounts"""
    condition: RoutingCondition
    target_account_ids: List[int]
    priority: int = 0
    name: Optional[str] = None  # Optional human-readable name
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingRule":
        """Create RoutingRule from dictionary (e.g., from JSON)"""
        condition_data = data.get("condition", {})
        condition = RoutingCondition(
            field=condition_data.get("field", "symbol"),
            operator=RoutingOperator(condition_data.get("operator", "eq")),
            value=condition_data.get("value")
        )

        # Handle both single target_account_id and list
        target_ids = data.get("target_account_ids", [])
        if not target_ids and "target_account_id" in data:
            target_ids = [data["target_account_id"]]

        return cls(
            condition=condition,
            target_account_ids=target_ids,
            priority=data.get("priority", 0),
            name=data.get("name"),
            description=data.get("description")
        )

    def matches(self, signal_data: Dict[str, Any]) -> bool:
        """Check if this rule matches the signal"""
        return self.condition.matches(signal_data)


@dataclass
class RoutingConfig:
    """Complete routing configuration for a webhook"""
    strategy: RoutingStrategy
    default_account_id: Optional[int] = None
    specific_account_ids: List[int] = field(default_factory=list)
    rules: List[RoutingRule] = field(default_factory=list)
    fallback_to_default: bool = True  # If rules don't match, use default

    @classmethod
    def from_webhook_config(cls, webhook_config: Any) -> "RoutingConfig":
        """Create RoutingConfig from WebhookConfig model"""
        # Determine strategy from config
        strategy_str = getattr(webhook_config, 'routing_strategy', None) or 'default_only'
        try:
            strategy = RoutingStrategy(strategy_str)
        except ValueError:
            strategy = RoutingStrategy.DEFAULT_ONLY

        # Parse routing rules from JSON
        rules = []
        routing_rules_data = getattr(webhook_config, 'routing_rules', None) or []
        if routing_rules_data:
            for rule_data in routing_rules_data:
                try:
                    rules.append(RoutingRule.from_dict(rule_data))
                except Exception as e:
                    logger.warning(f"Failed to parse routing rule: {e}")

        # Get specific account IDs
        specific_ids = getattr(webhook_config, 'specific_account_ids', None) or []

        return cls(
            strategy=strategy,
            default_account_id=getattr(webhook_config, 'default_account_id', None),
            specific_account_ids=specific_ids,
            rules=rules
        )


class RoutingEngine:
    """
    Evaluates routing configuration against signal data to determine target accounts.

    The engine supports multiple routing strategies:
    - ALL_ACCOUNTS: Returns all available accounts
    - SPECIFIC_ACCOUNTS: Returns only the specified account IDs
    - RULES_BASED: Evaluates rules against signal data
    - DEFAULT_ONLY: Returns only the default account
    """

    def __init__(self, config: RoutingConfig, available_accounts: List[int]):
        """
        Initialize routing engine.

        Args:
            config: Routing configuration
            available_accounts: List of account IDs available for routing
        """
        self.config = config
        self.available_accounts: Set[int] = set(available_accounts)

    def resolve_target_accounts(self, signal_data: Dict[str, Any]) -> List[int]:
        """
        Resolve which accounts should receive the signal.

        Args:
            signal_data: Dictionary containing signal information:
                - symbol: Trading symbol
                - action: Signal action (buy/sell/close)
                - source: Signal source
                - strategy_name: Strategy name (if available)
                - strategy_id: Strategy ID (if available)

        Returns:
            List of account IDs that should receive the signal
        """
        if self.config.strategy == RoutingStrategy.ALL_ACCOUNTS:
            return self._route_to_all()

        elif self.config.strategy == RoutingStrategy.SPECIFIC_ACCOUNTS:
            return self._route_to_specific()

        elif self.config.strategy == RoutingStrategy.DEFAULT_ONLY:
            return self._route_to_default()

        elif self.config.strategy == RoutingStrategy.RULES_BASED:
            return self._evaluate_rules(signal_data)

        logger.warning(f"Unknown routing strategy: {self.config.strategy}")
        return self._route_to_default()

    def _route_to_all(self) -> List[int]:
        """Route to all available accounts"""
        result = list(self.available_accounts)
        logger.debug(f"Routing to all accounts: {result}")
        return result

    def _route_to_specific(self) -> List[int]:
        """Route to specific configured accounts"""
        result = [
            aid for aid in self.config.specific_account_ids
            if aid in self.available_accounts
        ]
        logger.debug(f"Routing to specific accounts: {result}")
        return result

    def _route_to_default(self) -> List[int]:
        """Route to default account only"""
        if self.config.default_account_id and self.config.default_account_id in self.available_accounts:
            return [self.config.default_account_id]
        return []

    def _evaluate_rules(self, signal_data: Dict[str, Any]) -> List[int]:
        """
        Evaluate routing rules and return matching account IDs.

        Rules are evaluated in priority order (higher priority first).
        All matching rules contribute their target accounts.
        """
        matched_accounts: Set[int] = set()

        # Sort rules by priority (higher first)
        sorted_rules = sorted(self.config.rules, key=lambda r: -r.priority)

        for rule in sorted_rules:
            if rule.matches(signal_data):
                logger.debug(f"Rule matched: {rule.name or 'unnamed'} -> accounts {rule.target_account_ids}")
                for account_id in rule.target_account_ids:
                    if account_id in self.available_accounts:
                        matched_accounts.add(account_id)

        # Fallback to default if no rules matched and fallback is enabled
        if not matched_accounts and self.config.fallback_to_default:
            if self.config.default_account_id and self.config.default_account_id in self.available_accounts:
                logger.debug(f"No rules matched, falling back to default account: {self.config.default_account_id}")
                matched_accounts.add(self.config.default_account_id)

        result = list(matched_accounts)
        logger.debug(f"Rules-based routing result: {result}")
        return result

    def validate_config(self) -> List[str]:
        """
        Validate the routing configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check default account is available
        if self.config.default_account_id and self.config.default_account_id not in self.available_accounts:
            errors.append(f"Default account {self.config.default_account_id} is not available")

        # Check specific accounts are available
        for aid in self.config.specific_account_ids:
            if aid not in self.available_accounts:
                errors.append(f"Specific account {aid} is not available")

        # Check rule target accounts are available
        for rule in self.config.rules:
            for aid in rule.target_account_ids:
                if aid not in self.available_accounts:
                    errors.append(f"Rule target account {aid} is not available")

        # Warn if no accounts available
        if not self.available_accounts:
            errors.append("No accounts available for routing")

        return errors


def build_signal_data(payload: Dict[str, Any], webhook_source: str) -> Dict[str, Any]:
    """
    Build signal data dictionary from webhook payload for rule evaluation.

    Args:
        payload: Raw webhook payload
        webhook_source: Source of the webhook (tradingview, trailhacker, etc.)

    Returns:
        Normalized signal data for routing evaluation
    """
    return {
        "symbol": payload.get("ticker") or payload.get("symbol", ""),
        "action": (payload.get("action") or payload.get("signal", "")).lower(),
        "source": webhook_source,
        "strategy_name": payload.get("strategy_name", ""),
        "strategy_id": payload.get("strategy_id", ""),
        "quantity": payload.get("quantity") or payload.get("size") or payload.get("volume", 0),
        "price": payload.get("price") or payload.get("entry", 0),
    }
