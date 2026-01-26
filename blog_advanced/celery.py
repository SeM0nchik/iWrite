# blog_advanced/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_advanced.settings")

app = Celery("blog_advanced")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
