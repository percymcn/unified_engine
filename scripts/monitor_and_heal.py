#!/usr/bin/env python3
"""
Unified Trading Engine - Auto-Monitoring and Healing Service
Continuously monitors Docker Swarm services and auto-heals issues
"""

import subprocess
import time
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

# Configure logging
# Use /var/log if running as root, otherwise use local logs directory
if os.geteuid() == 0:
    LOG_DIR = Path("/var/log/unified_engine")
else:
    LOG_DIR = Path.home() / "unified_engine" / "logs" / "monitor"
LOG_DIR.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "monitor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("unified_monitor")

# Configuration
CHECK_INTERVAL = 30  # seconds
SERVICES_TO_MONITOR = [
    "unified_api",
    "unified_postgres",
    "unified_redis",
    "unified_celery-worker",
    "unified_celery-beat",
    "unified_ui",
    "unified_nats",
    "unified_nginx",
    "unified_flower",
    "unified_funnel-automation"
]

CRITICAL_SERVICES = ["unified_api", "unified_postgres", "unified_redis"]
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 300  # 5 minutes

# Track restart attempts
restart_history: Dict[str, List[float]] = {}


def run_command(cmd: str, timeout: int = 30) -> Optional[str]:
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except subprocess.TimeoutExpired:
        logger.error(f"Command timeout: {cmd}")
        return None
    except Exception as e:
        logger.error(f"Command failed: {cmd} - {e}")
        return None


def get_service_status() -> Dict[str, Dict]:
    """Get status of all monitored services"""
    status = {}

    for service in SERVICES_TO_MONITOR:
        # Get replicas
        replicas_output = run_command(
            f"docker service ls --filter name={service} --format '{{{{.Replicas}}}}'"
        )

        if not replicas_output:
            status[service] = {"status": "not_found", "replicas": "0/0"}
            continue

        # Parse replicas (e.g., "1/1" or "0/1")
        try:
            running, desired = replicas_output.split('/')
            running = running.split()[0] if ' ' in running else running  # Handle "1/1 (max 1 per node)"
            is_healthy = int(running) >= int(desired)
        except (ValueError, IndexError):
            is_healthy = False
            running, desired = "0", "0"

        # Get task state
        task_state = run_command(
            f"docker service ps {service} --filter 'desired-state=running' --format '{{{{.CurrentState}}}}' | head -1"
        )

        status[service] = {
            "status": "healthy" if is_healthy else "unhealthy",
            "replicas": replicas_output,
            "running": running,
            "desired": desired,
            "task_state": task_state or "unknown"
        }

    return status


def check_api_health() -> bool:
    """Check if API is responding to health checks"""
    result = run_command("curl -s --max-time 5 http://127.0.0.1:8765/health", timeout=10)
    if result and "healthy" in result:
        return True
    return False


def check_database_connectivity() -> bool:
    """Check if database is accessible"""
    result = run_command(
        "docker exec $(docker ps -q -f name=unified_postgres) pg_isready -U trading_user",
        timeout=10
    )
    return result is not None and "accepting connections" in result


def check_redis_connectivity() -> bool:
    """Check if Redis is accessible"""
    result = run_command(
        "docker exec $(docker ps -q -f name=unified_redis) redis-cli ping",
        timeout=10
    )
    return result == "PONG"


def can_restart_service(service: str) -> bool:
    """Check if service can be restarted based on cooldown and attempt limits"""
    now = time.time()

    if service not in restart_history:
        restart_history[service] = []

    # Clean old restart attempts outside cooldown window
    restart_history[service] = [
        t for t in restart_history[service]
        if now - t < RESTART_COOLDOWN
    ]

    # Check if we've exceeded max attempts in cooldown period
    if len(restart_history[service]) >= MAX_RESTART_ATTEMPTS:
        logger.warning(
            f"Service {service} has been restarted {len(restart_history[service])} times "
            f"in the last {RESTART_COOLDOWN}s. Skipping restart."
        )
        return False

    return True


def restart_service(service: str) -> bool:
    """Restart a Docker service"""
    if not can_restart_service(service):
        return False

    logger.info(f"Restarting service: {service}")
    result = run_command(f"docker service update --force {service}", timeout=120)

    if result is not None:
        restart_history[service].append(time.time())
        logger.info(f"Service {service} restart initiated")
        return True
    else:
        logger.error(f"Failed to restart service: {service}")
        return False


def check_system_resources() -> Dict[str, float]:
    """Check system resource usage"""
    resources = {}

    # CPU load average
    load_output = run_command("uptime | awk -F'load average:' '{print $2}' | awk '{print $1}'")
    if load_output:
        try:
            resources["load_avg"] = float(load_output.replace(',', ''))
        except ValueError:
            resources["load_avg"] = 0.0

    # Memory usage
    mem_output = run_command("free | grep Mem | awk '{print ($3/$2) * 100}'")
    if mem_output:
        try:
            resources["memory_percent"] = float(mem_output)
        except ValueError:
            resources["memory_percent"] = 0.0

    # Disk usage
    disk_output = run_command("df -h / | tail -1 | awk '{print $5}' | sed 's/%//'")
    if disk_output:
        try:
            resources["disk_percent"] = float(disk_output)
        except ValueError:
            resources["disk_percent"] = 0.0

    return resources


def cleanup_docker_resources():
    """Clean up Docker resources if disk usage is high"""
    logger.info("Running Docker cleanup...")

    # Remove stopped containers
    run_command("docker container prune -f", timeout=60)

    # Remove unused images
    run_command("docker image prune -af --filter 'until=24h'", timeout=120)

    # Remove unused volumes (be careful with this)
    run_command("docker volume prune -f", timeout=60)

    logger.info("Docker cleanup completed")


def heal_service(service: str, status: Dict) -> bool:
    """Attempt to heal a service based on its status"""
    logger.warning(f"Service {service} is unhealthy: {status}")

    # If service has 0 running replicas, restart it
    if int(status["running"]) == 0:
        logger.info(f"Service {service} has 0 replicas, attempting restart")
        return restart_service(service)

    # If task is in failed state, restart
    if "failed" in status["task_state"].lower():
        logger.info(f"Service {service} task failed, attempting restart")
        return restart_service(service)

    # If running but desired is higher, give it time to scale
    if int(status["running"]) < int(status["desired"]):
        logger.info(f"Service {service} is scaling up ({status['replicas']}), waiting...")
        return False

    return False


def check_and_heal():
    """Main monitoring and healing loop iteration"""
    logger.info("=" * 60)
    logger.info(f"Starting health check at {datetime.now()}")

    # Get service status
    service_status = get_service_status()

    # Check each service
    issues_found = []
    for service, status in service_status.items():
        if status["status"] == "unhealthy":
            issues_found.append(service)
            heal_service(service, status)
        else:
            logger.info(f"✓ {service}: {status['replicas']} - {status['task_state'][:50]}")

    # Check API health specifically
    if "unified_api" in [s for s, st in service_status.items() if st["status"] == "healthy"]:
        api_healthy = check_api_health()
        if not api_healthy:
            logger.warning("API service is running but not responding to health checks")
            issues_found.append("unified_api_health")

    # Check database connectivity
    db_connected = check_database_connectivity()
    if not db_connected:
        logger.error("Database is not accepting connections!")
        issues_found.append("database_connectivity")
        # Try restarting postgres
        if can_restart_service("unified_postgres"):
            restart_service("unified_postgres")

    # Check Redis connectivity
    redis_connected = check_redis_connectivity()
    if not redis_connected:
        logger.error("Redis is not responding!")
        issues_found.append("redis_connectivity")
        if can_restart_service("unified_redis"):
            restart_service("unified_redis")

    # Check system resources
    resources = check_system_resources()
    logger.info(f"System Resources: Load={resources.get('load_avg', 0):.2f}, "
                f"Memory={resources.get('memory_percent', 0):.1f}%, "
                f"Disk={resources.get('disk_percent', 0):.1f}%")

    # Auto-cleanup if disk usage is high
    if resources.get("disk_percent", 0) > 80:
        logger.warning(f"Disk usage high: {resources['disk_percent']}%")
        cleanup_docker_resources()

    # Log summary
    if issues_found:
        logger.warning(f"Issues detected: {', '.join(issues_found)}")
    else:
        logger.info("✓ All services healthy")

    logger.info("=" * 60)


def main():
    """Main monitoring loop"""
    logger.info("Starting Unified Trading Engine Monitor")
    logger.info(f"Monitoring {len(SERVICES_TO_MONITOR)} services every {CHECK_INTERVAL} seconds")
    logger.info(f"Critical services: {', '.join(CRITICAL_SERVICES)}")

    iteration = 0
    while True:
        try:
            iteration += 1
            logger.info(f"\n[Iteration {iteration}]")
            check_and_heal()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
