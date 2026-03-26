"""
Comparison Results Store - Phase 4
====================================

Persists and queries backtest comparison results for data-driven routing.

This store:
1. Saves comparison results by regime
2. Builds regime-specific engine rankings from actual performance data
3. Provides queryable interface for the router
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

logger = logging.getLogger(__name__)


class ComparisonResultsStore:
    """
    Persistent store for backtest comparison results.

    Phase 4: Enables data-driven routing by storing actual performance
    metrics by regime and providing engine rankings based on real results.
    """

    def __init__(self, storage_path: str = ".smartflow_data/comparisons"):
        """
        Initialize the comparison results store.

        Args:
            storage_path: Directory to store comparison results
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._regime_rankings: Dict[str, Dict[str, Any]] = {}
        self._comparison_history: List[Dict[str, Any]] = []

        # Load existing data
        self._load_regime_rankings()

        logger.info(f"ComparisonResultsStore initialized: {self.storage_path}")

    def save_comparison_result(self, comparison_result: Any) -> None:
        """
        Save a comparison result and update regime rankings.

        Args:
            comparison_result: ComparisonResult from comparison runner
        """
        from app.services.backtesting.comparison_runner import ComparisonResult

        if not isinstance(comparison_result, ComparisonResult):
            logger.error(f"Invalid comparison result type: {type(comparison_result)}")
            return

        # Save full comparison result to history
        comparison_data = {
            'comparison_id': comparison_result.comparison_id,
            'timestamp': comparison_result.timestamp.isoformat(),
            'ticker': comparison_result.ticker,
            'start_date': comparison_result.start_date,
            'end_date': comparison_result.end_date,
            'engines_compared': comparison_result.engines_compared,
            'leaderboard': comparison_result.leaderboard,
            'regime_comparison': comparison_result.regime_comparison,
            'warnings': comparison_result.warnings
        }

        # Save to file
        comparison_file = self.storage_path / f"{comparison_result.comparison_id}.json"
        with open(comparison_file, 'w') as f:
            json.dump(comparison_data, f, indent=2)

        logger.info(f"Saved comparison result: {comparison_result.comparison_id}")

        # Update regime rankings from this comparison
        self._update_regime_rankings_from_comparison(comparison_result)

    def _update_regime_rankings_from_comparison(self, comparison: Any) -> None:
        """
        Extract regime-specific rankings from a comparison result.

        Phase 4.5: Now aggregates statistics across multiple comparisons
        to build statistically reliable performance data.

        Args:
            comparison: ComparisonResult object
        """
        if not comparison.regime_comparison:
            logger.warning(f"No regime comparison data in {comparison.comparison_id}")
            return

        # Get overall engine results for additional metrics
        engine_results = comparison.engine_results

        # Process each regime
        for regime, engine_metrics in comparison.regime_comparison.items():
            if regime not in self._regime_rankings:
                self._regime_rankings[regime] = {
                    'ranked_engines': [],
                    'engine_stats': {},  # Phase 4.5: Per-engine aggregated stats
                    'sample_count': 0,
                    'last_updated': None,
                    'comparison_ids': []
                }

            regime_data = self._regime_rankings[regime]

            # Update sample count
            regime_data['sample_count'] += 1
            regime_data['last_updated'] = datetime.now().isoformat()

            if comparison.comparison_id not in regime_data['comparison_ids']:
                regime_data['comparison_ids'].append(comparison.comparison_id)

            # Phase 4.5: Aggregate statistics for each engine
            for engine, metrics in engine_metrics.items():
                if engine not in regime_data['engine_stats']:
                    regime_data['engine_stats'][engine] = {
                        'samples': 0,
                        'total_pnl': 0.0,
                        'total_win_rate': 0.0,
                        'pnl_history': [],
                        'win_rate_history': []
                    }

                stats = regime_data['engine_stats'][engine]
                stats['samples'] += 1

                # Accumulate metrics
                pnl = metrics.get('pnl', 0.0)
                win_rate = metrics.get('win_rate', 0.0)

                stats['total_pnl'] += pnl
                stats['total_win_rate'] += win_rate
                stats['pnl_history'].append(pnl)
                stats['win_rate_history'].append(win_rate)

                # Calculate averages
                stats['avg_pnl'] = stats['total_pnl'] / stats['samples']
                stats['avg_win_rate'] = stats['total_win_rate'] / stats['samples']

                # Get additional metrics from engine_results if available
                if engine in engine_results:
                    overall_metrics = engine_results[engine]
                    stats['latest_sharpe'] = overall_metrics.get('sharpe_ratio', 0.0)
                    stats['latest_return_pct'] = overall_metrics.get('total_return_pct', 0.0)

            # Rank engines by average P&L across all samples
            ranked = sorted(
                regime_data['engine_stats'].items(),
                key=lambda x: x[1].get('avg_pnl', 0),
                reverse=True
            )

            regime_data['ranked_engines'] = [engine for engine, _ in ranked]

            logger.info(
                f"Updated ranking for '{regime}' (samples={regime_data['sample_count']}): "
                f"{regime_data['ranked_engines']}"
            )

        # Persist regime rankings
        self._save_regime_rankings()

    def get_regime_ranking(self, regime: str) -> Optional[Dict[str, Any]]:
        """
        Get engine ranking for a specific regime.

        Args:
            regime: Market regime name

        Returns:
            Regime ranking data or None if not available
        """
        return self._regime_rankings.get(regime)

    def get_all_regime_rankings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all regime rankings.

        Returns:
            Dict mapping regime names to ranking data
        """
        return self._regime_rankings.copy()

    def has_data_for_regime(self, regime: str) -> bool:
        """
        Check if we have comparison data for a regime.

        Args:
            regime: Market regime name

        Returns:
            True if data exists
        """
        return regime in self._regime_rankings

    def get_ranking_summary(self) -> Dict[str, Any]:
        """
        Get summary of available rankings.

        Returns:
            Summary including regimes with data, sample counts, etc.
        """
        summary = {
            'total_regimes': len(self._regime_rankings),
            'regimes_with_data': list(self._regime_rankings.keys()),
            'regime_details': {}
        }

        for regime, data in self._regime_rankings.items():
            summary['regime_details'][regime] = {
                'ranked_engines': data['ranked_engines'],
                'sample_count': data['sample_count'],
                'last_updated': data['last_updated'],
                'comparisons': len(data['comparison_ids'])
            }

        return summary

    def _save_regime_rankings(self) -> None:
        """Persist regime rankings to disk."""
        rankings_file = self.storage_path / "regime_rankings.json"
        with open(rankings_file, 'w') as f:
            json.dump(self._regime_rankings, f, indent=2)
        logger.debug(f"Saved regime rankings to {rankings_file}")

    def _load_regime_rankings(self) -> None:
        """Load regime rankings from disk."""
        rankings_file = self.storage_path / "regime_rankings.json"

        if not rankings_file.exists():
            logger.info("No existing regime rankings found")
            return

        try:
            with open(rankings_file, 'r') as f:
                self._regime_rankings = json.load(f)
            logger.info(f"Loaded rankings for {len(self._regime_rankings)} regimes")
        except Exception as e:
            logger.error(f"Failed to load regime rankings: {e}")
            self._regime_rankings = {}

    def clear_all_data(self) -> None:
        """Clear all stored data (for testing/reset)."""
        self._regime_rankings = {}
        self._save_regime_rankings()

        # Remove all comparison files
        for file in self.storage_path.glob("comp_*.json"):
            file.unlink()

        logger.info("Cleared all comparison data")

    def get_comparison_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent comparison results.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of comparison summaries
        """
        comparison_files = sorted(
            self.storage_path.glob("comp_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        history = []
        for file in comparison_files[:limit]:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    history.append({
                        'comparison_id': data['comparison_id'],
                        'timestamp': data['timestamp'],
                        'ticker': data['ticker'],
                        'engines': data['engines_compared'],
                        'regimes': list(data.get('regime_comparison', {}).keys())
                    })
            except Exception as e:
                logger.error(f"Failed to load comparison file {file}: {e}")

        return history


# Global instance
_comparison_store: Optional[ComparisonResultsStore] = None


def get_comparison_store() -> ComparisonResultsStore:
    """Get or create global comparison store instance."""
    global _comparison_store
    if _comparison_store is None:
        _comparison_store = ComparisonResultsStore()
    return _comparison_store
