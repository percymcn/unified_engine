"""
Domain Entities

Domain entities represent the core business concepts with behavior and state.
Unlike database models, entities are rich domain models that encapsulate
business logic and enforce invariants.

Entities in this package:
- Signal: Trading signal with validation and processing logic
- Trade: Executed trade with P&L calculation
- Account: Trading account with balance management
- Position: Open position with risk management
- Order: Pending order with lifecycle management

Design Principles:
- Entities contain behavior, not just data
- Business rules are enforced within entities
- Entities are framework-independent (no ORM annotations)
- State changes are explicit and validated
- Entities can raise domain exceptions for invalid operations
"""

__all__ = []
