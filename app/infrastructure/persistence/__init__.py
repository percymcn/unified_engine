"""
Persistence Layer Package

Contains Unit of Work implementation and session management:
- SQLAlchemyUnitOfWork: Implements app.application.interfaces.unit_of_work.UnitOfWork
- SQLAlchemyUnitOfWorkFactory: Creates UnitOfWork instances with proper session management
- SessionManager: Manages SQLAlchemy session lifecycle

Responsibilities:
- Transaction management (commit, rollback)
- Repository instantiation within transaction context
- Database session lifecycle management
- Connection pooling configuration

Implementation in Plan 05-04.
"""

# Persistence layer exports
# Will be populated in Plan 05-04

__all__ = [
    # "SQLAlchemyUnitOfWork",
    # "SQLAlchemyUnitOfWorkFactory",
    # "SessionManager",
]
