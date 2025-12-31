from celery import Celery
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
    timezone='UTC',
    enable_utc=True,
)
