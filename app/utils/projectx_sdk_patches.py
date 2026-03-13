"""
ProjectX SDK Patches

Patches for the project-x-py SDK to handle API changes that haven't been
incorporated into the SDK yet.

These patches should be applied BEFORE any SDK usage.
"""

import logging
import sys

logger = logging.getLogger(__name__)


def apply_position_model_patch():
    """
    Patch Position model to accept contractDisplayName field.

    The ProjectX API started returning this field but the SDK v3.5.9
    doesn't have it in the Position dataclass, causing:
    'Position.__init__() got an unexpected keyword argument 'contractDisplayName''

    This patch replaces Position in all relevant SDK modules.
    """
    try:
        from dataclasses import dataclass, field
        from typing import Union

        @dataclass
        class PatchedPosition:
            """
            Patched Position model with contractDisplayName support.
            """
            id: int
            accountId: int
            contractId: str
            creationTimestamp: str
            type: int
            size: int
            averagePrice: float
            # New field from API that SDK doesn't have yet
            contractDisplayName: str | None = None
            symbolId: str | None = None

            _patched: bool = field(default=True, repr=False)

            def __getitem__(self, key: str) -> Union[int, str, float]:
                value = getattr(self, key)
                if isinstance(value, int | str | float):
                    return value
                else:
                    raise TypeError(
                        f"Attribute {key} has type {type(value)}, expected int, str, or float"
                    )

            @property
            def is_long(self) -> bool:
                """Check if this is a long position."""
                return self.type == 1

            @property
            def is_short(self) -> bool:
                """Check if this is a short position."""
                return self.type == 2

            @property
            def direction(self) -> str:
                """Get position direction as string."""
                if self.is_long:
                    return "LONG"
                elif self.is_short:
                    return "SHORT"
                else:
                    return "UNDEFINED"

            @property
            def symbol(self) -> str:
                """Extract symbol from contract ID."""
                if "." in self.contractId:
                    parts = self.contractId.split(".")
                    if len(parts) >= 4:
                        return parts[3]
                return self.contractId

            @property
            def signed_size(self) -> int:
                """Get size with sign (negative for short positions)."""
                return -self.size if self.is_short else self.size

            @property
            def total_cost(self) -> float:
                """Calculate total position cost."""
                return self.size * self.averagePrice

            def unrealized_pnl(self, current_price: float, tick_value: float = 1.0) -> float:
                """Calculate unrealized P&L given current price."""
                if self.is_long:
                    return (current_price - self.averagePrice) * self.size * tick_value
                elif self.is_short:
                    return (self.averagePrice - current_price) * self.size * tick_value
                else:
                    return 0.0

        # Patch all SDK modules that use Position
        modules_to_patch = [
            'project_x_py.models',
            'project_x_py.client.trading',
            'project_x_py.position_manager.core',
            'project_x_py.position_manager.tracking',
            'project_x_py.position_manager.operations',
            'project_x_py.position_manager.analytics',
            'project_x_py',
        ]

        patched_count = 0
        for module_name in modules_to_patch:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                if hasattr(module, 'Position'):
                    setattr(module, 'Position', PatchedPosition)
                    patched_count += 1
                    logger.debug(f"Patched Position in {module_name}")

        # Also import and patch directly to ensure future imports get patched version
        try:
            import project_x_py.models as models
            models.Position = PatchedPosition
            patched_count += 1
        except ImportError:
            pass

        try:
            import project_x_py.client.trading as trading
            trading.Position = PatchedPosition
            patched_count += 1
        except ImportError:
            pass

        if patched_count > 0:
            logger.info(f"ProjectX SDK Position model patched in {patched_count} locations (added contractDisplayName)")
            return True
        else:
            logger.warning("No Position references found to patch")
            return False

    except ImportError:
        logger.debug("project-x-py SDK not installed, skipping patch")
        return False
    except Exception as e:
        logger.error(f"Failed to patch Position model: {e}")
        return False


def apply_all_patches():
    """Apply all SDK patches."""
    patches_applied = 0

    if apply_position_model_patch():
        patches_applied += 1

    if patches_applied > 0:
        logger.info(f"Applied {patches_applied} ProjectX SDK patch(es)")

    return patches_applied
