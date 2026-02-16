from celery import Celery
from celery.schedules import crontab
import os

# Get Redis URL from environment
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery_app = Celery(
    'unified_trading',
    broker=redis_url,
    backend=redis_url,
    include=['app.tasks.trading_tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/New_York',  # EST/EDT timezone
    enable_utc=False,  # Use local timezone instead of UTC
    # Connection retry settings for Docker Swarm DNS timing
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'sync-all-accounts-every-5-minutes': {
        'task': 'trading_tasks.sync_all_accounts',
        'schedule': 300.0,  # Every 5 minutes (in seconds)
        'options': {
            'expires': 240,  # Task expires after 4 minutes
        }
    },
    'reset-daily-counters-at-market-close': {
        'task': 'trading_tasks.reset_daily_counters',
        'schedule': crontab(hour=18, minute=1),  # Daily at 6:01 PM EST/EDT (after 4pm close, before 6pm after-hours)
    },
}
