from celery import shared_task

from . import services


@shared_task
def recompute_recent_task(days=2):
    return services.recompute_recent(days=days)
