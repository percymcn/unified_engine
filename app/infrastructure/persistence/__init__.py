"""
Persistence Layer Package

Contains Unit of Work implementation and session management:
- SQLAlchemyUnitOfWork: Implements app.application.interfaces.unit_of_work.UnitOfWork
- SQLAlchemyUnitOfWorkFactory: Creates UnitOfWork instances with proper session management
- SessionFactory: Creates async database sessions

Responsibilities:
- Transaction management (commit, rollback)
- Repository instantiation within transaction context
- Database session lifecycle management
- Connection pooling configuration

Implemented in Plan 05-04.
"""

from app.infrastructure.persistence.session_factory import SessionFactory
from app.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
    SQLAlchemyUnitOfWorkFactory,
)

__all__ = [
    "SessionFactory",
    "SQLAlchemyUnitOfWork",
    "SQLAlchemyUnitOfWorkFactory",
]
