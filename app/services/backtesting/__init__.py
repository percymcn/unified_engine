"""Backtesting services package."""

from .comparison_runner import (
    ComparisonRunner,
    ComparisonResult,
    EngineExecutionMetadata,
    get_comparison_runner
)

__all__ = [
    'ComparisonRunner',
    'ComparisonResult',
    'EngineExecutionMetadata',
    'get_comparison_runner'
]
