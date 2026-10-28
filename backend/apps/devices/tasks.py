from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import Device, SyncLog
from .services import sync_device


@shared_task(bind=True, max_retries=5)
def sync_device_task(self, device_id, trigger=SyncLog.Trigger.AUTO):
    device = Device.objects.get(pk=device_id)
    result = sync_device(device, trigger)
    if not result.success and self.request.retries < self.max_retries:
        # exponential backoff: 30s, 60s, 120s... capped at 15 min
        raise self.retry(countdown=min(30 * 2 ** self.request.retries, 900))
    return result.pk


@shared_task
def dispatch_due_syncs():
    now = timezone.now()
    for d in Device.objects.filter(enabled=True, sync_interval_minutes__gt=0):
        due = d.last_sync_at is None or d.last_sync_at <= now - timedelta(minutes=d.sync_interval_minutes)
        if due:
            sync_device_task.delay(d.pk)
