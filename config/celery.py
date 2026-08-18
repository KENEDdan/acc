import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('acc_platform')
# Reads every CELERY_* setting from config/settings/*.py (CELERY_BROKER_URL etc.
# are already defined in base.py) — no separate Celery config file needed.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
