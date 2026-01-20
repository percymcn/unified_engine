"""
Docker Swarm Secrets Reader

Provides utilities to read secrets from Docker Swarm secrets (/run/secrets/)
with fallback to environment variables for development.

Usage:
    from app.core.secrets import get_secret

    db_password = get_secret("db_password")
    secret_key = get_secret("secret_key", default="dev-key")
"""
import os
from pathlib import Path
from typing import Optional


# Docker Swarm secrets directory
SECRETS_DIR = Path("/run/secrets")


def get_secret(name: str, default: Optional[str] = None) -> str:
    """
    Read a secret from Docker Swarm secrets or environment variables.

    Priority:
    1. /run/secrets/{name} (Docker Swarm secret file)
    2. Environment variable {NAME} (uppercase)
    3. Environment variable {NAME}_FILE (points to secret file path)
    4. default value

    Args:
        name: Secret name (e.g., "db_password")
        default: Default value if secret not found

    Returns:
        Secret value as string

    Raises:
        ValueError: If secret not found and no default provided

    Example:
        >>> get_secret("db_password")
        'secure_password_123'

        >>> get_secret("optional_key", default="fallback")
        'fallback'
    """
    # 1. Try Docker Swarm secret file
    secret_path = SECRETS_DIR / name
    if secret_path.exists() and secret_path.is_file():
        try:
            value = secret_path.read_text().strip()
            if value:
                return value
        except Exception as e:
            # Log but continue to fallback
            print(f"Warning: Failed to read secret file {secret_path}: {e}")

    # 2. Try environment variable (uppercase)
    env_name = name.upper()
    env_value = os.getenv(env_name)
    if env_value:
        return env_value

    # 3. Try _FILE suffix environment variable (points to file path)
    env_file_name = f"{env_name}_FILE"
    env_file_path = os.getenv(env_file_name)
    if env_file_path:
        try:
            file_path = Path(env_file_path)
            if file_path.exists() and file_path.is_file():
                value = file_path.read_text().strip()
                if value:
                    return value
        except Exception as e:
            print(f"Warning: Failed to read secret from {env_file_path}: {e}")

    # 4. Use default if provided
    if default is not None:
        return default

    # No secret found and no default - raise error
    raise ValueError(
        f"Secret '{name}' not found in:\n"
        f"  - {secret_path}\n"
        f"  - Environment variable: {env_name}\n"
        f"  - Environment variable: {env_file_name}\n"
        f"  - No default provided"
    )


def get_secret_or_none(name: str) -> Optional[str]:
    """
    Read a secret, returning None if not found.

    Convenience wrapper around get_secret() for optional secrets.

    Args:
        name: Secret name

    Returns:
        Secret value or None if not found

    Example:
        >>> get_secret_or_none("optional_api_key")
        None
    """
    try:
        return get_secret(name, default=None)
    except ValueError:
        return None


def has_secret(name: str) -> bool:
    """
    Check if a secret exists.

    Args:
        name: Secret name

    Returns:
        True if secret exists, False otherwise

    Example:
        >>> has_secret("db_password")
        True
    """
    try:
        get_secret(name)
        return True
    except ValueError:
        return False


def list_available_secrets() -> list[str]:
    """
    List all available Docker Swarm secrets.

    Returns:
        List of secret names found in /run/secrets/

    Example:
        >>> list_available_secrets()
        ['db_password', 'secret_key', 'jwt_secret']
    """
    if not SECRETS_DIR.exists():
        return []

    try:
        return [
            f.name
            for f in SECRETS_DIR.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
    except Exception:
        return []
