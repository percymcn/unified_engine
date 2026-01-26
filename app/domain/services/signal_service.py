"""
Signal Service - Domain Service

Orchestrates signal processing business logic through port interfaces.
No direct infrastructure dependencies.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.domain.entities.signal import Signal
from app.domain.entities.account import Account
from app.domain.ports.repository_port import SignalRepository, AccountRepository
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.event_port import EventPort, DomainEvent, EventType
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId
from app.domain.enums import SignalSource, SignalAction, SignalStatus, OrderType, BrokerType
from app.domain.exceptions import (
    SignalValidationError, SignalProcessingError, AccountNotFoundError,
    AccountDisabledError, BusinessRuleViolation
)

logger = logging.getLogger(__name__)


class SignalService:
    """
    Domain service for signal processing.

    Orchestrates signal validation, routing, and execution through port interfaces.
    This service has NO direct infrastructure dependencies - only ports.
    """

    def __init__(
        self,
        signal_repository: SignalRepository,
        account_repository: AccountRepository,
        brokers: Dict[BrokerType, BrokerPort],
        event_port: EventPort,
    ):
        self._signal_repo = signal_repository
        self._account_repo = account_repository
        self._brokers = brokers
        self._events = event_port

    async def process_signal(self, signal: Signal) -> Signal:
        """
        Process a trading signal.

        1. Validate signal
        2. Find target accounts
        3. Execute on each account
        4. Update signal status
        5. Publish events
        """
        try:
            # Mark as processing
            signal.mark_processing()
            await self._signal_repo.save(signal)

            # Publish received event
            await self._events.publish(DomainEvent.create(
                EventType.SIGNAL_RECEIVED,
                {"signal_id": signal.id.value, "action": signal.action.value},
                aggregate_id=signal.id.value,
            ))

            # Validate and get target accounts
            accounts = await self._get_target_accounts(signal)
            if not accounts:
                signal.mark_skipped("No active accounts for signal")
                await self._signal_repo.save(signal)
                return signal

            # Execute signal on each account
            execution_results = []
            for account in accounts:
                try:
                    result = await self._execute_on_account(signal, account)
                    execution_results.append({
                        "account_id": str(account.id.value),
                        "broker": account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
                        "success": bool(result.get("success")),
                        "error": result.get("error"),
                        "order_id": result.get("order_id"),
                    })
                except Exception as e:
                    logger.error(f"Failed to execute signal on account {account.id.value}: {e}")
                    execution_results.append({
                        "account_id": str(account.id.value),
                        "broker": account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
                        "success": False,
                        "error": str(e),
                    })

            # Update signal status based on results
            successes = [r for r in execution_results if r.get("success")]
            signal.execution_details = execution_results
            if successes:
                signal.mark_processed()
                await self._events.publish(DomainEvent.create(
                    EventType.SIGNAL_PROCESSED,
                    {"signal_id": signal.id.value, "executions": len(successes)},
                    aggregate_id=signal.id.value,
                ))
            else:
                errors = [r.get("error", "Unknown") for r in execution_results]
                signal.mark_failed("; ".join(errors))
                await self._events.publish(DomainEvent.create(
                    EventType.SIGNAL_FAILED,
                    {"signal_id": signal.id.value, "errors": errors},
                    aggregate_id=signal.id.value,
                ))

            await self._signal_repo.save(signal)
            return signal

        except Exception as e:
            logger.error(f"Signal processing error: {e}")
            signal.mark_failed(str(e))
            await self._signal_repo.save(signal)
            raise SignalProcessingError(f"Failed to process signal: {e}")

    async def _get_target_accounts(self, signal: Signal) -> List[Account]:
        """
        Get accounts to execute signal on, respecting account settings.

        Filters accounts by:
        - is_active: Account must be active
        - is_connected: Account must be connected
        - is_signal_enabled: Account must have signals enabled

        Sorts accounts by:
        - signal_priority: Higher priority accounts first
        """
        accounts = []

        if signal.target_accounts:
            # Specific accounts targeted by routing
            for account_id in signal.target_accounts:
                account = await self._account_repo.get_by_id(account_id)
                if self._account_can_receive_signal(account):
                    accounts.append(account)
        else:
            # All connected accounts (fallback)
            all_accounts = await self._account_repo.get_connected()
            accounts = [a for a in all_accounts if self._account_can_receive_signal(a)]

        # Sort by signal_priority (higher first)
        accounts.sort(key=lambda a: getattr(a, 'signal_priority', 0), reverse=True)

        return accounts

    def _account_can_receive_signal(self, account: Optional[Account]) -> bool:
        """
        Check if account can receive signals.

        Args:
            account: Account to check

        Returns:
            True if account can receive signals, False otherwise
        """
        if not account:
            return False
        if not account.is_active:
            return False
        if not account.is_connected:
            return False
        # Check is_signal_enabled (defaults to True for backward compatibility)
        if not getattr(account, 'is_signal_enabled', True):
            return False
        return True

    async def _execute_on_account(self, signal: Signal, account: Account) -> Dict[str, Any]:
        """Execute signal on a specific account"""
        broker = self._brokers.get(account.broker)
        if not broker:
            return {"success": False, "error": f"No broker adapter for {account.broker}"}

        if not await broker.is_connected():
            return {"success": False, "error": "Broker not connected"}

        # Convert signal action to order
        if signal.action == SignalAction.BUY:
            order_type = OrderType.BUY
        elif signal.action == SignalAction.SELL:
            order_type = OrderType.SELL
        elif signal.action == SignalAction.CLOSE:
            return await self._close_positions(broker, account, signal.symbol)
        elif signal.action == SignalAction.MODIFY:
            return await self._modify_positions(broker, account, signal)
        else:
            return {"success": False, "error": f"Unknown action: {signal.action}"}

        # Place order
        order = await broker.place_order(
            symbol=signal.symbol,
            order_type=order_type,
            volume=signal.volume,
            price=signal.price,
            stop_loss=signal.stop_loss.price if signal.stop_loss else None,
            take_profit=signal.take_profit.price if signal.take_profit else None,
            comment=signal.comment,
        )

        return {"success": True, "order_id": order.id.value}

    async def _close_positions(self, broker: BrokerPort, account: Account, symbol: Symbol) -> Dict[str, Any]:
        """Close all positions for symbol"""
        positions = await broker.get_positions()
        closed = 0
        for pos in positions:
            if pos.symbol.value == symbol.value:
                await broker.close_position(pos.id)
                closed += 1
        return {"success": True, "closed_positions": closed}

    async def _modify_positions(self, broker: BrokerPort, account: Account, signal: Signal) -> Dict[str, Any]:
        """Modify positions for symbol"""
        positions = await broker.get_positions()
        modified = 0
        for pos in positions:
            if pos.symbol.value == signal.symbol.value:
                await broker.modify_position(
                    pos.id,
                    stop_loss=signal.stop_loss.price if signal.stop_loss else None,
                    take_profit=signal.take_profit.price if signal.take_profit else None,
                )
                modified += 1
        return {"success": True, "modified_positions": modified}

    async def get_pending_signals(self, limit: int = 100) -> List[Signal]:
        """Get signals waiting for processing"""
        return await self._signal_repo.get_pending(limit)

    async def get_signal(self, signal_id: SignalId) -> Optional[Signal]:
        """Get signal by ID"""
        return await self._signal_repo.get_by_id(signal_id)
