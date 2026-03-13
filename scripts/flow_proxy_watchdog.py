#!/usr/bin/env python3
"""
FlowAlgo Proxy Watchdog
========================
Monitors the flow proxy for stale data and automatically restarts it.

Run via cron every 5 minutes:
*/5 * * * * /home/pharma5/unified_engine/flow_venv/bin/python3 /home/pharma5/unified_engine/scripts/flow_proxy_watchdog.py >> /var/log/flow_watchdog.log 2>&1
"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime, timedelta

import requests

# Configuration
FLOW_PROXY_URL = os.getenv("FLOW_PROXY_URL", "http://172.17.0.1:9001/recent")
STALE_THRESHOLD_MINUTES = 10  # Restart if data older than this
SERVICE_NAME = "flow_confluence_proxy"
LOG_FILE = "/var/log/flow_watchdog.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def get_latest_flow_timestamp() -> datetime | None:
    """Fetch latest flow timestamp from proxy."""
    try:
        response = requests.get(FLOW_PROXY_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        entries = data.get('entries', data) if isinstance(data, dict) else data

        if not entries:
            logger.warning("No flow entries found")
            return None

        # Find latest timestamp
        timestamps = []
        for entry in entries:
            if isinstance(entry, dict):
                ts_str = entry.get('timestamp', '')
                if ts_str:
                    try:
                        # Parse ISO format timestamp
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        timestamps.append(ts)
                    except ValueError:
                        pass

        if timestamps:
            return max(timestamps).replace(tzinfo=None)  # Remove tz for comparison

        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch flow data: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON response: {e}")
        return None


def is_data_stale(latest_ts: datetime | None) -> bool:
    """Check if flow data is stale."""
    if latest_ts is None:
        return True

    now = datetime.now()
    age = now - latest_ts
    age_minutes = age.total_seconds() / 60

    logger.info(f"Flow data age: {age_minutes:.1f} minutes (threshold: {STALE_THRESHOLD_MINUTES})")

    return age_minutes > STALE_THRESHOLD_MINUTES


def restart_flow_proxy() -> bool:
    """Restart the flow proxy service."""
    logger.warning("Restarting flow proxy service...")

    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("Flow proxy restarted successfully")
            return True
        else:
            logger.error(f"Failed to restart: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Restart command timed out")
        return False
    except Exception as e:
        logger.error(f"Restart failed: {e}")
        return False


def send_alert(message: str):
    """Send alert about flow proxy issues (optional: integrate with notification system)."""
    logger.warning(f"ALERT: {message}")
    # TODO: Add webhook notification, email, or SMS alert here


def main():
    """Main watchdog loop."""
    logger.info("=" * 60)
    logger.info("Flow Proxy Watchdog Check")
    logger.info("=" * 60)

    # Get latest flow timestamp
    latest_ts = get_latest_flow_timestamp()

    if latest_ts:
        logger.info(f"Latest flow timestamp: {latest_ts}")
    else:
        logger.warning("Could not determine latest flow timestamp")

    # Check if stale
    if is_data_stale(latest_ts):
        send_alert(f"Flow data is stale! Latest: {latest_ts}, Now: {datetime.now()}")

        # Restart the service
        if restart_flow_proxy():
            send_alert("Flow proxy restarted successfully")
        else:
            send_alert("CRITICAL: Failed to restart flow proxy!")
    else:
        logger.info("Flow data is fresh - no action needed")

    logger.info("Watchdog check complete")


if __name__ == "__main__":
    main()
