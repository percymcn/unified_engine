"""
Infrastructure mappers - bidirectional conversion between ORM and domain.

Mappers isolate persistence details from domain entities:
- to_entity(): ORM model → domain entity
- to_model(): domain entity → ORM model (for inserts/updates)
"""

__all__ = []
