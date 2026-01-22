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
    total_signals: int
    successful_signals: int
    failed_signals: int
    last_signal_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


def generate_webhook_key() -> str:
    """Generate secure random webhook key"""
    return secrets.token_urlsafe(32)


@router.get("/", response_model=List[WebhookConfigResponse])
async def get_webhook_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all webhook configurations for current user"""
    configs = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id
    ).all()
    return configs


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

    return db_config


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

    return config


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
    return config


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
    return config
