"""Webhook Configuration Router for Signal Routing"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel, Field
import secrets

from app.db.database import get_db
from app.models.database_models import WebhookConfig, TradingAccount
from app.models.models import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/webhook-configs", tags=["webhook-configs"])


# Pydantic Schemas
class RoutingCondition(BaseModel):
    """Condition for rule-based routing"""
    field: str = Field(..., description="Field to match: symbol, action, source, strategy_name")
    operator: str = Field(..., description="Operator: eq, neq, contains, starts_with, in, gt, lt")
    value: Any = Field(..., description="Value to compare against")


class RoutingRuleCreate(BaseModel):
    """Single routing rule"""
    condition: RoutingCondition
    target_account_id: int = Field(..., description="Account ID to route to if condition matches")
    priority: int = Field(0, description="Rule priority (higher = evaluated first)")
    name: Optional[str] = Field(None, description="Human-readable rule name")
    description: Optional[str] = Field(None, description="Rule description")


class WebhookConfigCreate(BaseModel):
    """Create a new webhook configuration"""
    name: str = Field(..., description="Display name for this webhook config")
    source: str = Field(..., description="Source: tradingview, trailhacker, or custom")
    routing_strategy: str = Field(
        "default_only",
        description="Routing strategy: all_accounts, specific_accounts, rules_based, default_only"
    )
    default_account_id: Optional[int] = Field(None, description="Default account for fallback")
    specific_account_ids: Optional[List[int]] = Field(None, description="Account IDs for specific_accounts strategy")
    routing_rules: Optional[List[dict]] = Field([], description="Routing rules for rules_based strategy")
    symbol_filter: Optional[List[str]] = Field(None, description="Symbols to accept (whitelist)")
    action_filter: Optional[List[str]] = Field(None, description="Actions to accept (whitelist)")
    is_active: bool = Field(True, description="Whether this config is active")


class WebhookConfigUpdate(BaseModel):
    """Update webhook configuration"""
    name: Optional[str] = None
    source: Optional[str] = None
    routing_strategy: Optional[str] = None
    default_account_id: Optional[int] = None
    specific_account_ids: Optional[List[int]] = None
    routing_rules: Optional[List[dict]] = None
    symbol_filter: Optional[List[str]] = None
    action_filter: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookConfigResponse(BaseModel):
    """Webhook configuration response"""
    id: int
    name: str
    webhook_key: str
    source: str
    routing_strategy: Optional[str] = "default_only"
    default_account_id: Optional[int] = None
    specific_account_ids: Optional[List[int]] = None
    routing_rules: Optional[List[dict]] = []
    symbol_filter: Optional[List[str]] = None
    action_filter: Optional[List[str]] = None
    is_active: bool
    total_signals: Optional[int] = 0
    successful_signals: Optional[int] = 0
    failed_signals: Optional[int] = 0
    last_signal_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


def generate_webhook_key() -> str:
    """Generate secure random webhook key"""
    return secrets.token_urlsafe(32)


def serialize_webhook_config(config: WebhookConfig) -> dict:
    """Serialize WebhookConfig ORM to response dict with ISO timestamps."""
    return {
        "id": config.id,
        "name": config.name,
        "webhook_key": config.webhook_key,
        "source": config.source,
        "routing_strategy": config.routing_strategy,
        "default_account_id": config.default_account_id,
        "specific_account_ids": config.specific_account_ids,
        "routing_rules": config.routing_rules,
        "symbol_filter": config.symbol_filter,
        "action_filter": config.action_filter,
        "is_active": config.is_active,
        "total_signals": config.total_signals,
        "successful_signals": config.successful_signals,
        "failed_signals": config.failed_signals,
        "last_signal_at": config.last_signal_at.isoformat() if config.last_signal_at else None,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@router.get("/", response_model=List[WebhookConfigResponse])
async def get_webhook_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all webhook configurations for current user"""
    configs = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id
    ).all()
    return [serialize_webhook_config(config) for config in configs]


@router.post("/", response_model=WebhookConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_config(
    config: WebhookConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new webhook configuration"""
    # Validate default_account_id if provided
    if config.default_account_id:
        account = db.query(TradingAccount).filter(
            TradingAccount.id == config.default_account_id,
            TradingAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default account not found"
            )

    # Validate specific account IDs if provided
    if config.specific_account_ids:
        for aid in config.specific_account_ids:
            account = db.query(TradingAccount).filter(
                TradingAccount.id == aid,
                TradingAccount.user_id == current_user.id
            ).first()
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Account {aid} not found in specific_account_ids"
                )

    # Validate target accounts in routing rules
    if config.routing_rules:
        for rule in config.routing_rules:
            if 'target_account_id' in rule:
                account = db.query(TradingAccount).filter(
                    TradingAccount.id == rule['target_account_id'],
                    TradingAccount.user_id == current_user.id
                ).first()
                if not account:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Account {rule['target_account_id']} not found in routing rules"
                    )

    # Validate routing_strategy
    valid_strategies = ['all_accounts', 'specific_accounts', 'rules_based', 'default_only']
    if config.routing_strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid routing_strategy. Must be one of: {valid_strategies}"
        )

    # Create webhook config
    db_config = WebhookConfig(
        user_id=current_user.id,
        name=config.name,
        webhook_key=generate_webhook_key(),
        source=config.source,
        routing_strategy=config.routing_strategy,
        default_account_id=config.default_account_id,
        specific_account_ids=config.specific_account_ids,
        routing_rules=config.routing_rules,
        symbol_filter=config.symbol_filter,
        action_filter=config.action_filter,
        is_active=config.is_active,
    )

    db.add(db_config)
    db.commit()
    db.refresh(db_config)

    return serialize_webhook_config(db_config)


@router.get("/{config_id}", response_model=WebhookConfigResponse)
async def get_webhook_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific webhook configuration"""
    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    return serialize_webhook_config(config)


@router.put("/{config_id}", response_model=WebhookConfigResponse)
async def update_webhook_config(
    config_id: int,
    config_update: WebhookConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update webhook configuration"""
    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    # Validate default_account_id if being updated
    if config_update.default_account_id is not None:
        account = db.query(TradingAccount).filter(
            TradingAccount.id == config_update.default_account_id,
            TradingAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default account not found"
            )

    # Validate specific account IDs if being updated
    if config_update.specific_account_ids is not None:
        for aid in config_update.specific_account_ids:
            account = db.query(TradingAccount).filter(
                TradingAccount.id == aid,
                TradingAccount.user_id == current_user.id
            ).first()
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Account {aid} not found in specific_account_ids"
                )

    # Validate target accounts in routing rules if being updated
    if config_update.routing_rules is not None:
        for rule in config_update.routing_rules:
            if 'target_account_id' in rule:
                account = db.query(TradingAccount).filter(
                    TradingAccount.id == rule['target_account_id'],
                    TradingAccount.user_id == current_user.id
                ).first()
                if not account:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Account {rule['target_account_id']} not found in routing rules"
                    )

    # Validate routing_strategy if being updated
    if config_update.routing_strategy is not None:
        valid_strategies = ['all_accounts', 'specific_accounts', 'rules_based', 'default_only']
        if config_update.routing_strategy not in valid_strategies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid routing_strategy. Must be one of: {valid_strategies}"
            )

    # Update fields
    for field, value in config_update.dict(exclude_unset=True).items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return serialize_webhook_config(config)


@router.delete("/{config_id}")
async def delete_webhook_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete webhook configuration"""
    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    db.delete(config)
    db.commit()
    return {"message": "Webhook configuration deleted successfully"}


@router.post("/{config_id}/generate-key", response_model=WebhookConfigResponse)
async def regenerate_webhook_key(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate webhook key for configuration"""
    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    # Generate new key
    config.webhook_key = generate_webhook_key()

    db.commit()
    db.refresh(config)
    return serialize_webhook_config(config)


# Routing-specific schemas
class RoutingUpdate(BaseModel):
    """Update routing configuration for a webhook"""
    strategy: str = Field(..., description="Routing strategy: all_accounts, specific_accounts, rules_based, default_only")
    default_account_id: Optional[int] = Field(None, description="Default account for fallback")
    specific_account_ids: Optional[List[int]] = Field(None, description="Account IDs for specific_accounts strategy")
    rules: Optional[List[dict]] = Field(None, description="Routing rules for rules_based strategy")


class RoutingResponse(BaseModel):
    """Routing configuration response"""
    strategy: str
    default_account_id: Optional[int] = None
    specific_account_ids: Optional[List[int]] = None
    rules: Optional[List[dict]] = None
    available_accounts: List[dict] = Field(default_factory=list, description="User's available accounts")


@router.get("/{config_id}/routing", response_model=RoutingResponse)
async def get_routing_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get routing configuration for a webhook.

    Returns the current routing strategy, rules, and available accounts.
    """
    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    # Get user's available accounts
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    available_accounts = [
        {
            "id": a.id,
            "name": a.account_name or f"Account {a.account_number}",
            "broker": a.broker.value if a.broker else "unknown",
            "is_signal_enabled": a.is_signal_enabled,
            "signal_priority": a.signal_priority or 0,
            "group_name": a.group_name
        }
        for a in accounts
    ]

    return RoutingResponse(
        strategy=config.routing_strategy or "default_only",
        default_account_id=config.default_account_id,
        specific_account_ids=config.specific_account_ids,
        rules=config.routing_rules,
        available_accounts=available_accounts
    )


@router.put("/{config_id}/routing")
async def update_routing(
    config_id: int,
    routing: RoutingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update webhook routing configuration.

    Allows updating the routing strategy without touching other webhook settings.

    **Strategies:**
    - `all_accounts`: Route to all active, signal-enabled accounts
    - `specific_accounts`: Route only to accounts in specific_account_ids
    - `rules_based`: Evaluate routing rules against signal data
    - `default_only`: Route only to the default account

    **Example rules_based configuration:**
    ```json
    {
        "strategy": "rules_based",
        "default_account_id": 1,
        "rules": [
            {
                "condition": {"field": "symbol", "operator": "eq", "value": "US30"},
                "target_account_id": 2,
                "priority": 10
            }
        ]
    }
    ```
    """
    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    # Validate strategy
    valid_strategies = ['all_accounts', 'specific_accounts', 'rules_based', 'default_only']
    if routing.strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy. Must be one of: {valid_strategies}"
        )

    # Validate default account if provided
    if routing.default_account_id:
        account = db.query(TradingAccount).filter(
            TradingAccount.id == routing.default_account_id,
            TradingAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Default account {routing.default_account_id} not found"
            )

    # Validate specific account IDs if provided
    if routing.specific_account_ids:
        for aid in routing.specific_account_ids:
            account = db.query(TradingAccount).filter(
                TradingAccount.id == aid,
                TradingAccount.user_id == current_user.id
            ).first()
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Account {aid} not found"
                )

    # Validate rule target accounts if provided
    if routing.rules:
        for rule in routing.rules:
            target_id = rule.get('target_account_id')
            if target_id:
                account = db.query(TradingAccount).filter(
                    TradingAccount.id == target_id,
                    TradingAccount.user_id == current_user.id
                ).first()
                if not account:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Rule target account {target_id} not found"
                    )

    # Update routing configuration
    config.routing_strategy = routing.strategy
    config.default_account_id = routing.default_account_id
    config.specific_account_ids = routing.specific_account_ids
    config.routing_rules = routing.rules

    db.commit()

    return {
        "message": "Routing updated successfully",
        "strategy": config.routing_strategy,
        "default_account_id": config.default_account_id,
        "specific_account_ids": config.specific_account_ids,
        "rules_count": len(config.routing_rules) if config.routing_rules else 0
    }


@router.post("/{config_id}/routing/test")
async def test_routing(
    config_id: int,
    signal_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test routing configuration with sample signal data.

    Simulates routing without actually executing a signal.
    Returns which accounts would receive the signal.

    **Example request:**
    ```json
    {
        "symbol": "US30",
        "action": "buy",
        "strategy_name": "My Strategy"
    }
    ```
    """
    from app.domain.services.routing_service import (
        RoutingEngine,
        RoutingConfig,
        build_signal_data,
    )

    config = db.query(WebhookConfig).filter(
        WebhookConfig.id == config_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )

    # Get user's active, signal-enabled accounts
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True,
        TradingAccount.is_signal_enabled == True
    ).all()

    available_account_ids = [a.id for a in accounts]
    account_lookup = {a.id: a for a in accounts}

    # Build routing configuration
    routing_config = RoutingConfig.from_webhook_config(config)

    # Create routing engine
    engine = RoutingEngine(routing_config, available_account_ids)

    # Build signal data
    test_signal_data = build_signal_data(signal_data, config.source)

    # Resolve target accounts
    target_account_ids = engine.resolve_target_accounts(test_signal_data)

    # Build response with account details
    target_accounts = []
    for aid in target_account_ids:
        account = account_lookup.get(aid)
        if account:
            target_accounts.append({
                "id": aid,
                "name": account.account_name or f"Account {account.account_number}",
                "broker": account.broker.value if account.broker else "unknown"
            })

    return {
        "signal_data": test_signal_data,
        "routing_strategy": config.routing_strategy,
        "target_account_ids": target_account_ids,
        "target_accounts": target_accounts,
        "would_be_routed": len(target_account_ids) > 0
    }
