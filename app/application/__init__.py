"""
Application Layer - Use Cases and Service Orchestration

This layer contains:
- Use cases: Application-specific business rules
- DTOs: Data Transfer Objects for API boundaries
- Interfaces: Contracts for external dependencies

The application layer depends on the domain layer but has NO
direct infrastructure dependencies (no FastAPI, SQLAlchemy, etc.).
"""

# Use cases will be imported here as they're created
# from app.application.use_cases import SomeUseCase

__all__ = []
