"""
Infrastructure Layer.

Implements domain ports with concrete adapters:
- adapters/: Broker implementations (BrokerPort)
- repositories/: SQLAlchemy implementations (Repository ports)
- persistence/: Unit of Work (transaction management)
- events/: Event publishers (EventPort)
- container.py: DI wiring
"""
from app.infrastructure.container import (
    Container,
    get_container,
    initialize_container,
    shutdown_container,
)

# Re-export subpackages for convenience
from app.infrastructure import adapters
from app.infrastructure import repositories
from app.infrastructure import persistence
from app.infrastructure import events

__all__ = [
    # Container
    "Container",
    "get_container",
    "initialize_container",
    "shutdown_container",
    # Subpackages
    "adapters",
    "repositories",
    "persistence",
    "events",
]
