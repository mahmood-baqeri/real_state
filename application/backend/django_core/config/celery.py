# application/backend/config/celery.py
import os
from celery import Celery

# خواندن از متغیر محیطی، در غیر این صورت پیش‌فرض local
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("realestate_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()