"""
Infrastructure Layer

Implements domain ports with concrete adapters for external systems.
This layer depends on the domain layer but the domain never depends on infrastructure.

Hexagonal Architecture:
- Domain defines ports (BrokerPort, EventPort, Repository interfaces)
- Infrastructure provides adapters (MT4Adapter, NATSEventPublisher, SQLAlchemyRepositories)
- Application layer receives infrastructure adapters via dependency injection

Subpackages:
- adapters: Broker adapter implementations (BrokerPort)
- repositories: SQLAlchemy repository implementations (Repository)
- persistence: Unit of Work and session management
- events: Event publisher implementations (EventPort)
"""

# Infrastructure layer exports
# Will be populated as adapters are implemented in subsequent plans

__all__ = [
    # Broker adapters (Phase 5, Plans 06-10)
    # EventPublishers (Phase 5, Plan 05)
    # Repositories (Phase 5, Plan 03)
    # UnitOfWork (Phase 5, Plan 04)
]
