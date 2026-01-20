"""
Application Interfaces

Abstract interfaces that the application layer depends on.
These are implemented by the infrastructure layer.
"""

from app.application.interfaces.unit_of_work import (
    UnitOfWork,
    UnitOfWorkFactory,
)

__all__ = [
    "UnitOfWork",
    "UnitOfWorkFactory",
]
