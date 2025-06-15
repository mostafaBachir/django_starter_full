# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'send-daily-notifications': {
        'task': 'apps.accounts.tasks.send_daily_notification_summary',
        'schedule': crontab(hour=9, minute=0),  # Tous les jours à 9h
    },
    'cleanup-expired-tokens': {
        'task': 'apps.accounts.tasks.cleanup_expired_password_reset_tokens',
        'schedule': crontab(hour=2, minute=0),  # Tous les jours à 2h du matin
    },
}
