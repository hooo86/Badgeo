from celery import shared_task

from . import services


@shared_task
def sauvegarde_planifiee_task():
    return services.sauvegarde_planifiee()
