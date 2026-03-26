"""
Variant Generator Service - Phase 6B
======================================

Generates parameterized variants of base strategies with:
- Auto-versioning (deterministic_v1 → deterministic_v1.1, v1.2, etc.)
- Parameter change tracking
- Candidate limit enforcement
- Hypothesis documentation
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.strategy_registry.registry import StrategyRegistry, get_strategy_registry
from app.services.strategy_registry.schemas import (
    StrategyCreate,
    StrategyStatus,
    StrategyType,
    VariantGenerateRequest,
    VariantGenerateResponse,
)

logger = logging.getLogger(__name__)


class VariantGenerator:
    """
    Generates strategy variants from base strategies.

    Handles:
    - Auto-versioning (v1 → v1.1, v1.2, ...)
    - Parameter merging (parent + changes)
    - Candidate limit enforcement
    - Hypothesis tracking
    """

    def __init__(self, registry: Optional[StrategyRegistry] = None):
        """Initialize generator with registry."""
        self.registry = registry or get_strategy_registry()
        logger.info("VariantGenerator initialized")

    def generate_variant(
        self,
        request: VariantGenerateRequest
    ) -> VariantGenerateResponse:
        """
        Generate a new strategy variant from a base strategy.

        Args:
            request: Variant generation request

        Returns:
            Generated variant response

        Raises:
            ValueError: If parent not found, candidate limit exceeded, or invalid parameters
        """
        # Get parent strategy
        parent = self.registry.get_strategy(request.parent_strategy_id)
        if not parent:
            raise ValueError(f"Parent strategy not found: {request.parent_strategy_id}")

        # Check candidate limits
        stats = self.registry.get_candidate_stats(request.parent_strategy_id)
        if not stats.can_create_more:
            raise ValueError(
                f"Candidate limit reached for {request.parent_strategy_id}: "
                f"{stats.active_candidates}/{stats.max_candidates}. "
                f"Approve, reject, or retire existing candidates before creating more."
            )

        # Generate variant ID and version
        variant_id, variant_version = self._generate_variant_id_and_version(
            parent.strategy_id,
            parent.strategy_type
        )

        # Merge parameters
        merged_parameters = self._merge_parameters(
            parent.parameters,
            request.parameter_changes
        )

        # Validate merged parameters
        self._validate_parameters(
            parent.strategy_type,
            merged_parameters,
            request.parameter_changes
        )

        # Create variant
        variant_create = StrategyCreate(
            strategy_id=variant_id,
            strategy_type=StrategyType(parent.strategy_type),
            version=variant_version,
            status=StrategyStatus.CANDIDATE,
            parameters=merged_parameters,
            parent_strategy_id=request.parent_strategy_id,
            parameter_changes=request.parameter_changes,
            hypothesis=request.hypothesis,
            created_by=request.created_by
        )

        variant = self.registry.create_strategy(variant_create)

        logger.info(
            f"Generated variant {variant_id} from {request.parent_strategy_id} "
            f"(changes: {list(request.parameter_changes.keys())})"
        )

        # Return response
        return VariantGenerateResponse(
            strategy_id=variant.strategy_id,
            strategy_type=variant.strategy_type,
            version=variant.version,
            status=variant.status,
            parameters=variant.parameters,
            parent_strategy_id=variant.parent_strategy_id,
            parameter_changes=variant.parameter_changes,
            hypothesis=variant.hypothesis,
            created_at=variant.created_at
        )

    def _generate_variant_id_and_version(
        self,
        parent_id: str,
        strategy_type: str
    ) -> tuple[str, str]:
        """
        Generate variant ID and version number.

        Examples:
            deterministic_v1 → deterministic_v1.1, v1.1.0
            deterministic_v1 → deterministic_v1.2, v1.2.0 (if v1.1 exists)

        Args:
            parent_id: Parent strategy ID (e.g., "deterministic_v1")
            strategy_type: Strategy type

        Returns:
            (variant_id, variant_version)
        """
        # Parse parent version
        # Expected format: {type}_v{major}.{minor}.{patch} or {type}_v{major}
        parts = parent_id.split('_v')
        if len(parts) != 2:
            raise ValueError(f"Invalid parent ID format: {parent_id}")

        base_name = parts[0]
        parent_version = parts[1]

        # Count existing variants for this parent
        existing_variants = self.registry.list_strategies(
            parent_strategy_id=parent_id
        )

        # Generate next minor version
        next_minor = len(existing_variants) + 1
        variant_version = f"{parent_version}.{next_minor}.0"
        variant_id = f"{base_name}_v{parent_version}.{next_minor}"

        # Check if variant_id already exists (defensive)
        if self.registry.get_strategy(variant_id):
            # Increment until we find an available ID
            counter = next_minor + 1
            while self.registry.get_strategy(f"{base_name}_v{parent_version}.{counter}"):
                counter += 1
            variant_id = f"{base_name}_v{parent_version}.{counter}"
            variant_version = f"{parent_version}.{counter}.0"

        return variant_id, variant_version

    def _merge_parameters(
        self,
        parent_params: Dict[str, Any],
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge parent parameters with changes.

        Args:
            parent_params: Parent strategy parameters
            changes: Parameter changes for variant

        Returns:
            Merged parameters
        """
        merged = parent_params.copy()
        merged.update(changes)
        return merged

    def _validate_parameters(
        self,
        strategy_type: str,
        parameters: Dict[str, Any],
        changes: Dict[str, Any]
    ) -> None:
        """
        Validate parameters for a strategy type.

        Args:
            strategy_type: Strategy type
            parameters: Merged parameters
            changes: Parameter changes

        Raises:
            ValueError: If parameters are invalid
        """
        # Ensure at least one parameter changed
        if not changes:
            raise ValueError("Variant must change at least one parameter from parent")

        # Type-specific validation
        if strategy_type == 'deterministic':
            self._validate_deterministic_params(parameters)
        elif strategy_type == 'quick':
            self._validate_quick_params(parameters)
        elif strategy_type == 'flow':
            self._validate_flow_params(parameters)
        elif strategy_type == 'ai':
            self._validate_ai_params(parameters)
        elif strategy_type == 'unified':
            self._validate_unified_params(parameters)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    def _validate_deterministic_params(self, params: Dict[str, Any]) -> None:
        """Validate deterministic strategy parameters."""
        required = ['min_aligned_timeframes', 'min_confidence_score', 'min_risk_reward']
        for key in required:
            if key not in params:
                raise ValueError(f"Deterministic strategy missing required parameter: {key}")

        # Range checks
        if not (1 <= params['min_aligned_timeframes'] <= 5):
            raise ValueError("min_aligned_timeframes must be between 1 and 5")
        if not (0 <= params['min_confidence_score'] <= 100):
            raise ValueError("min_confidence_score must be between 0 and 100")
        if not (0 < params['min_risk_reward'] <= 10):
            raise ValueError("min_risk_reward must be between 0 and 10")

    def _validate_quick_params(self, params: Dict[str, Any]) -> None:
        """Validate quick strategy parameters."""
        required = ['min_confidence_score', 'min_risk_reward', 'max_hold_hours']
        for key in required:
            if key not in params:
                raise ValueError(f"Quick strategy missing required parameter: {key}")

        # Range checks
        if not (0 <= params['min_confidence_score'] <= 100):
            raise ValueError("min_confidence_score must be between 0 and 100")
        if not (0 < params['min_risk_reward'] <= 10):
            raise ValueError("min_risk_reward must be between 0 and 10")
        if not (0 < params['max_hold_hours'] <= 24):
            raise ValueError("max_hold_hours must be between 0 and 24")

    def _validate_flow_params(self, params: Dict[str, Any]) -> None:
        """Validate flow strategy parameters."""
        required = ['score_threshold_buy', 'score_threshold_sell', 'min_premium']
        for key in required:
            if key not in params:
                raise ValueError(f"Flow strategy missing required parameter: {key}")

        # Range checks
        if params['score_threshold_buy'] <= 0:
            raise ValueError("score_threshold_buy must be positive")
        if params['score_threshold_sell'] >= 0:
            raise ValueError("score_threshold_sell must be negative")
        if params['min_premium'] < 0:
            raise ValueError("min_premium must be non-negative")

    def _validate_ai_params(self, params: Dict[str, Any]) -> None:
        """Validate AI strategy parameters."""
        required = ['min_confidence_score']
        for key in required:
            if key not in params:
                raise ValueError(f"AI strategy missing required parameter: {key}")

        # Range checks
        if not (0 <= params['min_confidence_score'] <= 100):
            raise ValueError("min_confidence_score must be between 0 and 100")

    def _validate_unified_params(self, params: Dict[str, Any]) -> None:
        """Validate unified strategy parameters."""
        required = ['score_threshold_buy', 'score_threshold_sell', 'min_confidence_score']
        for key in required:
            if key not in params:
                raise ValueError(f"Unified strategy missing required parameter: {key}")

        # Range checks
        if params['score_threshold_buy'] <= 0:
            raise ValueError("score_threshold_buy must be positive")
        if params['score_threshold_sell'] >= 0:
            raise ValueError("score_threshold_sell must be negative")
        if not (0 <= params['min_confidence_score'] <= 100):
            raise ValueError("min_confidence_score must be between 0 and 100")


# Global instance
_variant_generator: Optional[VariantGenerator] = None


def get_variant_generator() -> VariantGenerator:
    """Get or create global variant generator."""
    global _variant_generator
    if _variant_generator is None:
        _variant_generator = VariantGenerator()
    return _variant_generator
