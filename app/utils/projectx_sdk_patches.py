"""
ProjectX SDK Patches

Patches for the project-x-py SDK to handle API changes that haven't been
incorporated into the SDK yet.

These patches should be applied before any SDK usage.
"""

import logging

logger = logging.getLogger(__name__)


def apply_position_model_patch():
    """
    Patch Position model to accept contractDisplayName field.

    The ProjectX API started returning this field but the SDK v3.5.9
    doesn't have it in the Position dataclass, causing:
    'Position.__init__() got an unexpected keyword argument 'contractDisplayName''
    """
    try:
        from project_x_py import models
        from dataclasses import dataclass, field
        from typing import Union

        # Check if already patched
        if hasattr(models.Position, '_patched'):
            logger.debug("Position model already patched")
            return True

        # Store original class reference
        OriginalPosition = models.Position

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

        # Replace the Position class in the models module
        models.Position = PatchedPosition

        # Also update __all__ export if needed
        if 'Position' in models.__all__:
            # Already exported, patched class will be used
            pass

        logger.info("ProjectX SDK Position model patched successfully (added contractDisplayName)")
        return True

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
