import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoCore.settings")

app = Celery("DjangoCore")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
