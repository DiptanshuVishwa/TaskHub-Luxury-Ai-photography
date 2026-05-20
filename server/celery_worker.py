from celery import Celery
from config import Config

def make_celery(app_name=__name__):
    celery = Celery(
        app_name,
        backend=Config.CELERY_RESULT_BACKEND,
        broker=Config.CELERY_BROKER_URL
    )
    celery.conf.update(
        broker_connection_retry_on_startup=True,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    return celery

celery_app = make_celery()

# Only import tasks if running inside the Celery worker daemon
import sys
is_celery = any('celery' in arg for arg in sys.argv) or (len(sys.argv) > 0 and 'celery' in sys.argv[0])

if is_celery:
    import tasks.worker

