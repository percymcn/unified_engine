# Unified Trading Engine - Auto-Monitoring System

## Overview

The auto-monitoring system continuously watches your Docker Swarm services and automatically heals issues. It runs 24/7 and can:

- ✅ Detect unhealthy services (0 replicas, failed tasks)
- ✅ Auto-restart failed services
- ✅ Monitor API health endpoints
- ✅ Check database and Redis connectivity
- ✅ Track system resources (CPU, memory, disk)
- ✅ Auto-cleanup Docker resources when disk is high
- ✅ Prevent restart loops with cooldown periods
- ✅ Log all actions for troubleshooting

## Quick Start

### Option 1: Run as Background Process (Recommended for Testing)

```bash
# Start the monitor
./scripts/monitor_control.sh start

# Check status
./scripts/monitor_control.sh status

# View live logs
./scripts/monitor_control.sh logs

# Stop the monitor
./scripts/monitor_control.sh stop
```

### Option 2: Install as Systemd Service (Recommended for Production)

```bash
# Install the service (requires sudo)
sudo ./scripts/monitor_control.sh install-systemd

# Start the service
sudo systemctl start unified-monitor

# Enable to start on boot
sudo systemctl enable unified-monitor

# Check status
sudo systemctl status unified-monitor

# View logs
sudo journalctl -u unified-monitor -f
# or
tail -f /var/log/unified_engine/monitor.log
```

## Monitored Services

The system monitors these services:

- **unified_api** - Main API service (CRITICAL)
- **unified_postgres** - Database (CRITICAL)
- **unified_redis** - Cache (CRITICAL)
- **unified_celery-worker** - Task worker
- **unified_celery-beat** - Task scheduler
- **unified_ui** - Web interface
- **unified_nats** - Event bus
- **unified_nginx** - Reverse proxy
- **unified_flower** - Celery monitor
- **unified_funnel-automation** - Automation service

## Auto-Healing Actions

### Service Failures
- **0 replicas**: Immediately restarts the service
- **Failed tasks**: Restarts the service
- **Scaling issues**: Waits and monitors

### Health Check Failures
- **API not responding**: Logs warning (service will auto-restart via Docker health check)
- **Database unreachable**: Attempts to restart postgres
- **Redis unreachable**: Attempts to restart redis

### Resource Issues
- **Disk usage > 80%**: Automatically cleans up:
  - Stopped containers
  - Unused images (older than 24h)
  - Unused volumes

### Restart Protection
- **Max 3 restarts per service** within 5-minute window
- Prevents restart loops
- Logs warnings when limit reached

## Configuration

### Monitoring Intervals

Edit `scripts/monitor_and_heal.py`:

```python
CHECK_INTERVAL = 30  # Check every 30 seconds
RESTART_COOLDOWN = 300  # 5-minute cooldown between restarts
MAX_RESTART_ATTEMPTS = 3  # Max restarts in cooldown period
```

### Alert Configuration

Edit `scripts/alert_config.json`:

```json
{
  "enabled": true,
  "thresholds": {
    "cpu_load_avg": 3.0,
    "memory_percent": 90.0,
    "disk_percent": 85.0
  }
}
```

## Logs

### Log Locations

- **Background mode**: `~/unified_engine/logs/monitor/monitor.log`
- **Systemd mode**: `/var/log/unified_engine/monitor.log`
- **Systemd journal**: `journalctl -u unified-monitor`

### Log Format

```
2026-02-24 11:34:19,132 - unified_monitor - INFO - Starting health check
2026-02-24 11:34:19,763 - unified_monitor - WARNING - Service unified_api is unhealthy
2026-02-24 11:34:19,764 - unified_monitor - INFO - Restarting service: unified_api
2026-02-24 11:34:51,180 - unified_monitor - INFO - ✓ unified_postgres: 1/1
```

## Troubleshooting

### Monitor Not Starting

```bash
# Check if already running
./scripts/monitor_control.sh status

# Check Python dependencies
python3 scripts/monitor_and_heal.py --help

# Check Docker access
docker service ls
```

### Services Keep Restarting

Check the logs to see why:

```bash
tail -100 ~/unified_engine/logs/monitor/monitor.log | grep -A 5 "unhealthy"
```

Common causes:
- External API timeouts (TradeLocker, etc.)
- Memory/resource limits
- Network connectivity issues
- Database connection pool exhaustion

### Monitor Stops Unexpectedly

If running in background mode, it may have crashed. Check:

```bash
cat ~/unified_engine/logs/monitor/monitor_stdout.log
```

For production, use systemd mode which auto-restarts.

## Advanced Usage

### Manual Testing

Run one iteration manually:

```bash
# Test for 35 seconds (1 iteration)
timeout 35 python3 scripts/monitor_and_heal.py
```

### Custom Alerts

To add webhook or email alerts, modify `scripts/monitor_and_heal.py`:

```python
def send_alert(message: str, severity: str = "warning"):
    """Send alert via configured method"""
    # Add your webhook/email logic here
    logger.warning(f"ALERT [{severity}]: {message}")
```

### Integration with Existing Monitoring

The monitor logs are structured and can be parsed by:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Prometheus + Grafana
- Datadog
- New Relic

## Performance Impact

The monitor is lightweight:
- **CPU**: < 1% (limited to 20% via systemd)
- **Memory**: ~50-100MB (limited to 512MB via systemd)
- **Disk I/O**: Minimal (logs only)

## Security Considerations

- Runs as root (required for Docker API access)
- Logs may contain service names and errors
- No sensitive data (API keys, passwords) in logs
- All actions are logged for audit

## Best Practices

1. ✅ **Use systemd in production** - Auto-restarts if monitor crashes
2. ✅ **Monitor the monitor** - Set up external checks for the monitor service itself
3. ✅ **Review logs regularly** - Catch patterns before they become issues
4. ✅ **Adjust thresholds** - Based on your workload and resources
5. ✅ **Test recovery** - Occasionally test by stopping services manually

## Support

For issues or questions:
1. Check logs first: `./scripts/monitor_control.sh logs`
2. Review service status: `docker service ls`
3. Check system resources: `htop` or `docker stats`

## Changelog

### v1.0.0 (2026-02-24)
- Initial release
- Auto-healing for service failures
- Health check monitoring
- Resource monitoring
- Docker cleanup automation
- Restart protection
- Structured logging
