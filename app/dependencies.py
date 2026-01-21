"""
FastAPI Dependencies for Dependency Injection.

Provides access to the global DI Container from route handlers.
"""
from fastapi import Request

from app.infrastructure.container import Container


def get_container(request: Request) -> Container:
    """
    Get the global container instance from application state.

    Usage in route handlers:
        @router.post("/signals")
        async def process_signal(
            signal_data: dict,
            container: Container = Depends(get_container)
        ):
            use_case = container.process_signal_use_case()
            result = await use_case.execute(signal_data)
            return result

    Args:
        request: FastAPI request object with app state

    Returns:
        Container: Initialized DI container

    Raises:
        RuntimeError: If container not initialized
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("Container not initialized. Check lifespan startup.")

    return request.app.state.container
