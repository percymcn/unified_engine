"""
Infrastructure Layer.

Implements domain ports with concrete adapters:
- adapters/: Broker implementations (BrokerPort)
- repositories/: SQLAlchemy implementations (Repository ports)
- persistence/: Unit of Work (transaction management)
- events/: Event publishers (EventPort)
- container.py: DI wiring (import explicitly when needed)

IMPORTANT: Do not import container at module level to avoid SQLAlchemy model conflicts.
Container imports all adapters and repositories, which triggers database_models.py loading.
If container is imported alongside routes (which import models.py), SQLAlchemy will raise
"Table already defined" errors due to duplicate User table definitions.

To use container, import explicitly:
    from app.infrastructure.container import get_container
"""

# Don't import container at module level to avoid triggering model imports
# Container should be imported explicitly in main.py/startup only

__all__ = [
    "adapters",
    "repositories",
    "persistence",
    "events",
]
