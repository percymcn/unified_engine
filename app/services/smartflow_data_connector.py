"""
SmartFlow Data Connector Service
================================

Runs continuously in Docker Swarm to fetch and process:
1. Polygon Options Flow - Institutional options trading data
2. Unusual Whales Flow - Alternative flow data source
3. Publishes data to NATS for real-time consumption

This service keeps SmartFlow fed with live market data.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Configure logging for service mode
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SmartFlowDataConnector:
    """
    Unified data connector that manages all SmartFlow data sources.
    """

    def __init__(self):
        self.running = False
        self.polygon_flow = None
        self.unusual_whales = None
        self.nats_client = None

    async def start(self):
        """Start all data connectors."""
        logger.info("Starting SmartFlow Data Connector Service...")
        self.running = True

        # Initialize data sources
        await self._init_polygon()
        await self._init_unusual_whales()
        await self._init_nats()

        # Start background tasks
        tasks = [
            asyncio.create_task(self._run_polygon_loop()),
            asyncio.create_task(self._run_unusual_whales_loop()),
            asyncio.create_task(self._health_check_loop()),
        ]

        logger.info("SmartFlow Data Connector running. Press Ctrl+C to stop.")

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Data connector shutting down...")
        finally:
            await self.stop()

    async def stop(self):
        """Stop all data connectors."""
        self.running = False
        logger.info("SmartFlow Data Connector stopped.")

    async def _init_polygon(self):
        """Initialize Polygon Options Flow service."""
        try:
            from app.services.polygon_options_flow import get_polygon_flow_service
            self.polygon_flow = get_polygon_flow_service()
            logger.info("Polygon Options Flow service initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Polygon flow: {e}")

    async def _init_unusual_whales(self):
        """Initialize Unusual Whales service."""
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service_sync
            self.unusual_whales = get_unusual_whales_service_sync()
            logger.info(f"Unusual Whales service initialized (configured: {self.unusual_whales._is_configured})")
        except Exception as e:
            logger.warning(f"Could not initialize Unusual Whales: {e}")

    async def _init_nats(self):
        """Initialize NATS client for publishing."""
        nats_url = os.getenv('NATS_URL', 'nats://localhost:4222')
        try:
            import nats
            self.nats_client = await nats.connect(nats_url)
            logger.info(f"Connected to NATS at {nats_url}")
        except Exception as e:
            logger.warning(f"Could not connect to NATS: {e}")

    async def _run_polygon_loop(self):
        """Continuously fetch Polygon options flow data."""
        tickers = ['SPY', 'QQQ', 'IWM', 'DIA', 'GLD', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META']

        while self.running:
            try:
                if self.polygon_flow:
                    # Fetch and process flow for each ticker
                    for ticker in tickers:
                        try:
                            clusters = await self.polygon_flow.analyze_ticker(ticker)
                            if clusters:
                                await self._publish_flow_data('polygon', ticker, clusters)
                        except Exception as e:
                            logger.debug(f"Error analyzing {ticker}: {e}")

                # Sleep between cycles
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polygon loop error: {e}")
                await asyncio.sleep(60)

    async def _run_unusual_whales_loop(self):
        """Continuously fetch Unusual Whales flow data."""
        # Tickers to monitor for flow
        tickers = ['SPY', 'QQQ', 'IWM', 'DIA', 'GLD', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META']

        while self.running:
            try:
                if self.unusual_whales:
                    # Fetch market-wide flow
                    try:
                        flow_data = await self.unusual_whales.get_live_flow(tickers=tickers, min_premium=50000)
                        if flow_data:
                            await self._publish_flow_data('unusual_whales', 'flow', [f.__dict__ if hasattr(f, '__dict__') else str(f) for f in flow_data])
                    except Exception as e:
                        logger.debug(f"Error fetching UW live flow: {e}")

                    # Fetch market tide sentiment
                    try:
                        tide = await self.unusual_whales.get_market_tide()
                        if tide:
                            await self._publish_flow_data('unusual_whales', 'market_tide', tide)
                    except Exception as e:
                        logger.debug(f"Error fetching UW market tide: {e}")

                    # Fetch per-ticker flow for major indices
                    for ticker in ['SPY', 'QQQ', 'DIA']:
                        try:
                            flow_summary = await self.unusual_whales.get_flow_by_ticker(ticker)
                            if flow_summary:
                                summary_dict = {
                                    'ticker': flow_summary.ticker,
                                    'net_premium': flow_summary.net_premium,
                                    'sentiment_score': flow_summary.sentiment_score,
                                    'sentiment': flow_summary.overall_sentiment.value,
                                    'call_premium': flow_summary.call_premium,
                                    'put_premium': flow_summary.put_premium,
                                    'large_trades': flow_summary.large_trades_count,
                                    'whale_trades': flow_summary.whale_trades_count,
                                }
                                await self._publish_flow_data('unusual_whales', ticker.lower(), summary_dict)
                        except Exception as e:
                            logger.debug(f"Error fetching UW flow for {ticker}: {e}")

                # Sleep between cycles
                await asyncio.sleep(60)  # Check every 60 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unusual Whales loop error: {e}")
                await asyncio.sleep(120)

    async def _health_check_loop(self):
        """Periodic health check and logging."""
        while self.running:
            try:
                status = {
                    'polygon': self.polygon_flow is not None,
                    'unusual_whales': self.unusual_whales is not None,
                    'nats': self.nats_client is not None and self.nats_client.is_connected,
                    'timestamp': datetime.utcnow().isoformat()
                }
                logger.info(f"Health check: {status}")

                await asyncio.sleep(300)  # Every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)

    async def _publish_flow_data(self, source: str, ticker: str, data: any):
        """Publish flow data to NATS for consumption by other services."""
        if self.nats_client and self.nats_client.is_connected:
            try:
                import json
                subject = f"smartflow.{source}.{ticker.lower()}"
                payload = json.dumps({
                    'source': source,
                    'ticker': ticker,
                    'data': data if isinstance(data, (dict, list)) else str(data),
                    'timestamp': datetime.utcnow().isoformat()
                })
                await self.nats_client.publish(subject, payload.encode())
            except Exception as e:
                logger.debug(f"Failed to publish to NATS: {e}")


async def main():
    """Main entry point for the data connector service."""
    connector = SmartFlowDataConnector()

    try:
        await connector.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await connector.stop()


if __name__ == "__main__":
    asyncio.run(main())
