"""
Domain Ports - Hexagonal Architecture Interfaces

Ports define the contracts (interfaces) that infrastructure adapters must implement.
This inverts dependencies: the domain defines what it needs, and infrastructure
adapts to provide it.

Port Categories:
- Repository Ports: Data persistence contracts (ISignalRepository, IAccountRepository)
- Broker Ports: Trading execution contracts (IBrokerExecutor, IBrokerConnection)
- Notification Ports: Messaging contracts (INotificationService, IWebSocketManager)
- Cache Ports: Caching contracts (ICacheService)

Design Principles:
- Ports are abstract base classes (ABC) defining contracts
- Ports have no implementation, only interface definitions
- Infrastructure adapters implement these ports
- Domain services depend only on ports, never on concrete implementations
- This enables dependency injection and testability
"""

__all__ = []
