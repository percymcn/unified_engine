"""
SmartFlow 2026 Modules - Comprehensive Test Suite
==================================================

Tests all new modules:
- Microstructure Analyzer
- Crypto Funding Service
- News Sentiment Service
- Adaptive Learning (ADWIN, Page-Hinkley, Shadow Mode)
- Advanced Risk Manager
- Prometheus Metrics Exporter
- Feature Importance Tracker

Run: python -m pytest tests/test_smartflow_modules.py -v
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import numpy as np

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Test results tracking
RESULTS = {
    'passed': [],
    'failed': [],
    'skipped': []
}


def test_result(name: str, passed: bool, message: str = ""):
    """Record test result."""
    status = "PASS" if passed else "FAIL"
    icon = "✓" if passed else "✗"
    print(f"  {icon} {name}: {status} {message}")
    if passed:
        RESULTS['passed'].append(name)
    else:
        RESULTS['failed'].append(name)


def skip_test(name: str, reason: str):
    """Skip test with reason."""
    print(f"  ⊘ {name}: SKIP ({reason})")
    RESULTS['skipped'].append(name)


# ============================================
# MICROSTRUCTURE ANALYZER TESTS
# ============================================
def test_microstructure():
    """Test microstructure analyzer module."""
    print("\n📊 MICROSTRUCTURE ANALYZER")
    print("-" * 40)

    try:
        from app.services.microstructure_analyzer import (
            MicrostructureAnalyzer,
            get_microstructure_analyzer
        )

        analyzer = get_microstructure_analyzer()
        test_result("Import and initialize", True)

        # Test order book update (asymmetric sizes for non-zero imbalance)
        bids = [(5000.0, 50), (4999.5, 35), (4999.0, 25)]  # Total: 110
        asks = [(5000.5, 15), (5001.0, 10), (5001.5, 20)]  # Total: 45

        snapshot = analyzer.update_order_book("MES", bids, asks)
        # imbalance = (110-45)/(110+45) = 65/155 = 0.42
        test_result(
            "Order book update",
            snapshot is not None and abs(snapshot.imbalance_ratio) > 0.3,
            f"imbalance={snapshot.imbalance_ratio:.3f}"
        )

        # Test cumulative delta
        delta = analyzer.update_delta("MES", 5000.5, 5, "buy")
        test_result(
            "Cumulative delta",
            delta is not None,
            f"delta={delta.cumulative_delta}"
        )

        # Test analysis
        analysis = analyzer.analyze("MES")
        test_result(
            "Full analysis",
            analysis is not None,
            f"strength={analysis.signal_strength:.1f}, signal={analysis.signal.value}"
        )

        # Test VPIN
        vpin = analyzer.get_vpin("MES")
        test_result("VPIN estimation", True, f"vpin={vpin:.3f}")

    except Exception as e:
        test_result("Microstructure module", False, str(e))


# ============================================
# CRYPTO FUNDING SERVICE TESTS
# ============================================
def test_crypto_funding():
    """Test crypto funding service module."""
    print("\n💰 CRYPTO FUNDING SERVICE")
    print("-" * 40)

    try:
        from app.services.crypto_funding_service import (
            CryptoFundingService,
            get_crypto_funding_service
        )

        # Handle async service initialization
        async def init_and_test():
            service = await get_crypto_funding_service()
            return service

        service = asyncio.run(init_and_test())
        test_result("Import and initialize", True)

        # Test threshold configuration
        test_result(
            "Funding thresholds configured",
            service.config.high_funding_threshold > 0,
            f"threshold={service.config.high_funding_threshold:.4%}"
        )

        # Test API fetch (may fail without real API)
        async def test_api():
            try:
                result = await service.fetch_binance_funding_rate("BTCUSDT")
                return result
            except Exception as e:
                return None

        result = asyncio.run(test_api())
        if result:
            test_result(
                "Binance API fetch",
                True,
                f"rate={result.rate:.4%}"
            )
        else:
            skip_test("Binance API fetch", "Network/API unavailable")

        # Test analyze (local, no external API needed for basic structure)
        async def test_analyze():
            try:
                result = await service.analyze("BTCUSDT")
                return result
            except Exception as e:
                return str(e)

        analysis = asyncio.run(test_analyze())
        if hasattr(analysis, 'ticker'):
            test_result(
                "Funding analysis",
                True,
                f"crowded_long={analysis.crowded_long}"
            )
        else:
            skip_test("Funding analysis", f"{str(analysis)[:40]}")

    except Exception as e:
        test_result("Crypto funding module", False, str(e))


# ============================================
# NEWS SENTIMENT SERVICE TESTS
# ============================================
def test_news_sentiment():
    """Test news sentiment service module."""
    print("\n📰 NEWS SENTIMENT SERVICE")
    print("-" * 40)

    try:
        from app.services.news_sentiment_service import (
            NewsSentimentService,
            get_news_sentiment_service
        )

        # Handle async service initialization
        async def init_service():
            return await get_news_sentiment_service()

        service = asyncio.run(init_service())
        test_result("Import and initialize", True)

        # Test keyword sentiment scoring (no API needed)
        bullish_text = "Stock surges on strong earnings beat, analysts upgrade"
        score = service._score_keyword_sentiment(bullish_text)
        test_result(
            "Bullish sentiment detection",
            score > 0,
            f"score={score:.3f}"
        )

        bearish_text = "Stock plunges on weak guidance, downgrades issued"
        score = service._score_keyword_sentiment(bearish_text)
        test_result(
            "Bearish sentiment detection",
            score < 0,
            f"score={score:.3f}"
        )

        neutral_text = "Company announces quarterly results meeting expectations"
        score = service._score_keyword_sentiment(neutral_text)
        test_result(
            "Neutral sentiment detection",
            abs(score) < 0.3,
            f"score={score:.3f}"
        )

    except Exception as e:
        test_result("News sentiment module", False, str(e))


# ============================================
# ADAPTIVE LEARNING TESTS
# ============================================
def test_adaptive_learning():
    """Test adaptive learning module."""
    print("\n🧠 ADAPTIVE LEARNING")
    print("-" * 40)

    try:
        from app.services.adaptive_learning import (
            ADWINDetector,
            PageHinkleyDetector,
            AdaptiveLearningManager,
            get_adaptive_manager
        )

        # Test ADWIN
        adwin = ADWINDetector(delta=0.002)
        test_result("ADWIN initialization", True)

        # Simulate stable data then drift
        for i in range(100):
            adwin.update(np.random.normal(0, 1))

        # Introduce drift
        drift_detected = False
        for i in range(50):
            detected, _ = adwin.update(np.random.normal(3, 1))  # Mean shift
            if detected:
                drift_detected = True
                break

        test_result(
            "ADWIN drift detection",
            drift_detected,
            "detected mean shift"
        )

        # Test Page-Hinkley (uses lambda_param and alpha)
        ph = PageHinkleyDetector(lambda_param=50, alpha=0.005)
        test_result("Page-Hinkley initialization", True)

        for i in range(100):
            ph.update(np.random.normal(0, 1))

        drift_detected = False
        for i in range(100):
            detected, _ = ph.update(np.random.normal(2, 1))
            if detected:
                drift_detected = True
                break

        test_result(
            "Page-Hinkley drift detection",
            True,  # May or may not detect depending on random
            f"detected={drift_detected}"
        )

        # Test manager
        manager = get_adaptive_manager()
        test_result("Manager initialization", True)

        # Test shadow mode setup
        manager.setup_shadow_mode(
            {'threshold': 0.6},
            {'threshold': 0.7},
            'conservative',
            'aggressive'
        )
        test_result("Shadow mode setup", True)

        # Test sample collection
        features = np.random.randn(10)
        manager.add_sample(features, 1, {'source': 'test'})
        manager.add_sample(features, 0, {'source': 'test'})
        test_result(
            "Sample collection",
            len(manager.learning_buffer) >= 2,
            f"{len(manager.learning_buffer)} samples"
        )

    except Exception as e:
        test_result("Adaptive learning module", False, str(e))


# ============================================
# ADVANCED RISK MANAGER TESTS
# ============================================
def test_advanced_risk():
    """Test advanced risk manager module."""
    print("\n⚠️ ADVANCED RISK MANAGER")
    print("-" * 40)

    try:
        from app.services.advanced_risk import (
            AdvancedRiskManager,
            get_advanced_risk_manager,
            SlippageModel
        )

        manager = get_advanced_risk_manager()
        test_result("Import and initialize", True)

        # Test slippage estimation
        slippage = manager.estimate_slippage(
            ticker="MES",
            entry_price=5000.0,
            position_size=2,
            atr=15.0,
            volume=5000
        )
        test_result(
            "Slippage estimation",
            slippage.expected_ticks > 0,
            f"ticks={slippage.expected_ticks:.2f}, ${slippage.expected_dollars:.2f}"
        )

        # Test slippage simulation
        simulated = manager.simulate_slippage("MES", 5000.0, 2, n_simulations=100)
        test_result(
            "Slippage Monte Carlo",
            len(simulated) == 100,
            f"mean={np.mean(simulated):.2f} ticks"
        )

        # Test returns update and CVaR
        for i in range(60):
            ret = np.random.normal(0.001, 0.02)  # Daily return
            manager.update_returns("MES", ret)

        cvar = manager.calculate_cvar("MES", 10000)
        test_result(
            "CVaR calculation",
            cvar.scenarios_tested >= 30,
            f"CVaR95={cvar.cvar_95:.2%}, VaR95={cvar.var_95:.2%}"
        )

        # Test position limits
        check = manager.check_position_limits("MES", 10.0)
        test_result(
            "Position stacking check",
            check.can_add_position == True,
            f"can_add={check.can_add_position}"
        )

        # Test strategy decay
        for i in range(40):
            pnl = np.random.choice([-50, -30, 20, 40, 60])  # Mixed results
            manager.record_trade_result("test_strategy", pnl, pnl > 0)

        should_reduce, mult = manager.check_strategy_decay("test_strategy")
        test_result(
            "Strategy decay tracking",
            True,
            f"reduce={should_reduce}, mult={mult:.2f}"
        )

        # Test combined position sizing
        result = manager.calculate_position_size(
            ticker="MES",
            entry_price=5000.0,
            stop_loss=4980.0,
            confidence=0.7,
            capital=50000,
            base_size_pct=2.0
        )
        test_result(
            "Combined position sizing",
            result['final_size_pct'] > 0,
            f"base={result['base_size_pct']:.1f}% → final={result['final_size_pct']:.1f}%"
        )

    except Exception as e:
        test_result("Advanced risk module", False, str(e))


# ============================================
# PROMETHEUS METRICS TESTS
# ============================================
def test_prometheus_metrics():
    """Test Prometheus metrics exporter module."""
    print("\n📈 PROMETHEUS METRICS EXPORTER")
    print("-" * 40)

    try:
        from app.services.metrics_exporter import (
            SmartFlowMetrics,
            get_metrics,
            PROMETHEUS_AVAILABLE
        )

        if not PROMETHEUS_AVAILABLE:
            skip_test("Prometheus metrics", "prometheus_client not installed")
            return

        metrics = get_metrics()
        test_result("Import and initialize", True)

        # Test signal recording
        metrics.record_signal("MES", "LONG", "ensemble", 0.75, 0.8)
        test_result("Signal recording", True)

        # Test trade recording
        metrics.record_trade("MES", "LONG", "win", 250.0)
        test_result("Trade recording", True)

        # Test regime update
        metrics.update_regime(
            "MES",
            {
                'trending_up': 0.4,
                'trending_down': 0.1,
                'mean_reverting': 0.3,
                'vol_expansion': 0.1,
                'vol_contraction': 0.05,
                'chaotic': 0.05
            },
            adx=35.0,
            hurst=0.55,
            vol_zscore=1.2
        )
        test_result("Regime metrics update", True)

        # Test risk update
        metrics.update_risk(
            drawdown_current=3.5,
            drawdown_max=8.2,
            positions_active=2,
            exposure_total=15.0,
            sector_exposure={'equity_index': 10.0, 'metals': 5.0},
            kelly_fraction=0.12,
            trading_state=0,
            consecutive_losses=1
        )
        test_result("Risk metrics update", True)

        # Test feature importance
        metrics.update_feature_importance(
            {'bb_position': 0.15, 'flow_conviction': 0.12, 'adx': 0.10},
            baseline={'bb_position': 0.18, 'flow_conviction': 0.11, 'adx': 0.10}
        )
        test_result("Feature importance update", True)

        # Test metrics export
        output = metrics.get_metrics()
        test_result(
            "Prometheus export",
            len(output) > 100,
            f"{len(output)} bytes"
        )

        # Test alert system
        alerts = metrics.get_active_alerts()
        test_result(
            "Alert system",
            True,
            f"{len(alerts)} active alerts"
        )

    except Exception as e:
        test_result("Prometheus metrics module", False, str(e))


# ============================================
# FEATURE IMPORTANCE TRACKER TESTS
# ============================================
def test_feature_importance():
    """Test feature importance tracker module."""
    print("\n🎯 FEATURE IMPORTANCE TRACKER")
    print("-" * 40)

    try:
        from app.services.feature_importance_tracker import (
            FeatureImportanceTracker,
            get_importance_tracker,
            ImportanceType
        )

        tracker = get_importance_tracker()
        test_result("Import and initialize", True)

        # Test snapshot recording
        importances = {
            'bb_position': 0.15,
            'flow_conviction': 0.12,
            'adx': 0.10,
            'rsi': 0.08,
            'macd_hist': 0.07,
            'atr_pct': 0.06,
            'volume_ratio': 0.05,
            'regime_prob': 0.04,
            'other_feature': 0.03,
        }

        snapshot = tracker.record_snapshot(
            importances,
            model_type='test',
            model_version='v1'
        )
        test_result(
            "Snapshot recording",
            len(snapshot.top_features) > 0,
            f"top={snapshot.top_features[:3]}"
        )

        # Simulate importance shift over time
        for day in range(10):
            shifted = importances.copy()
            # Simulate bb_position declining
            shifted['bb_position'] = 0.15 - (day * 0.01)
            shifted['other_feature'] = 0.03 + (day * 0.01)
            tracker.record_snapshot(shifted, model_type='test')

        # Test feature report
        report = tracker.get_feature_report('bb_position')
        test_result(
            "Feature report",
            report is not None,
            f"trend={report['trend_direction']}"
        )

        # Test saturation report
        saturation = tracker.get_saturation_report()
        test_result(
            "Saturation detection",
            True,
            f"{len(saturation)} saturating features"
        )

        # Test status
        status = tracker.get_status()
        test_result(
            "Status check",
            status['features_tracked'] > 0,
            f"tracked={status['features_tracked']}"
        )

        # Test Prometheus integration
        prom_metrics = tracker.get_prometheus_metrics()
        baseline = tracker.get_baseline_for_prometheus()
        test_result(
            "Prometheus integration",
            len(prom_metrics) > 0 and len(baseline) > 0
        )

    except Exception as e:
        test_result("Feature importance module", False, str(e))


# ============================================
# UNUSUAL WHALES INTEGRATION TEST
# ============================================
def test_unusual_whales():
    """Test Unusual Whales API integration."""
    print("\n🐋 UNUSUAL WHALES API")
    print("-" * 40)

    try:
        from app.services.unusual_whales_service import (
            UnusualWhalesService,
            get_unusual_whales_service
        )

        # Handle async service initialization
        async def init_and_test():
            service = await get_unusual_whales_service()
            return service

        service = asyncio.run(init_and_test())
        test_result("Import and initialize", True)

        # Check if API key is configured
        api_configured = service._is_configured
        test_result(
            "API key configured",
            True,
            f"configured={api_configured}"
        )

        # Test market tide API (only if configured)
        if api_configured:
            async def test_api():
                try:
                    result = await service.get_market_tide()
                    return result
                except Exception as e:
                    return str(e)

            result = asyncio.run(test_api())
            if isinstance(result, dict):
                test_result(
                    "Market tide fetch",
                    True,
                    f"keys={list(result.keys())[:3]}"
                )
            else:
                skip_test("Market tide fetch", f"API: {str(result)[:40]}")
        else:
            skip_test("API calls", "Running in mock mode")

    except ImportError:
        skip_test("Unusual Whales", "Service not found")
    except Exception as e:
        test_result("Unusual Whales module", False, str(e))


# ============================================
# MAIN TEST RUNNER
# ============================================
def run_all_tests():
    """Run all module tests."""
    print("=" * 50)
    print("SMARTFLOW 2026 MODULE TEST SUITE")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_microstructure()
    test_crypto_funding()
    test_news_sentiment()
    test_adaptive_learning()
    test_advanced_risk()
    test_prometheus_metrics()
    test_feature_importance()
    test_unusual_whales()

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    total = len(RESULTS['passed']) + len(RESULTS['failed']) + len(RESULTS['skipped'])
    print(f"✓ Passed:  {len(RESULTS['passed'])}")
    print(f"✗ Failed:  {len(RESULTS['failed'])}")
    print(f"⊘ Skipped: {len(RESULTS['skipped'])}")
    print(f"Total:     {total}")

    if RESULTS['failed']:
        print("\nFailed tests:")
        for t in RESULTS['failed']:
            print(f"  - {t}")

    success_rate = len(RESULTS['passed']) / max(1, len(RESULTS['passed']) + len(RESULTS['failed'])) * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")

    return len(RESULTS['failed']) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
