"""Planificateur léger pour l'édition locale (remplace Celery beat + worker, sans Redis).

Un thread exécute chaque tâche à sa cadence ; une erreur dans une tâche est journalisée et n'arrête jamais les autres."""
import logging
import threading
import time

log = logging.getLogger("badgeo.scheduler")


def _syncs():
    from datetime import timedelta

    from django.utils import timezone

    from apps.devices.models import Device
    from apps.devices.services import sync_device

    now = timezone.now()
    for d in Device.objects.filter(enabled=True, sync_interval_minutes__gt=0):
        if d.last_sync_at is None or d.last_sync_at <= now - timedelta(minutes=d.sync_interval_minutes):
            sync_device(d)  # échec : état enregistré, nouvel essai au prochain cycle


def _recalcul():
    from apps.attendance.services import recompute_recent
    recompute_recent(days=2)


def _sauvegarde():
    from apps.backups.services import sauvegarde_planifiee
    sauvegarde_planifiee()


TACHES = [("synchronisation des pointeuses", 60, _syncs), ("recalcul des présences", 300, _recalcul),
          ("sauvegarde planifiée", 600, _sauvegarde)]


def demarrer():
    def boucle():
        derniere = {nom: 0.0 for nom, _, _ in TACHES}
        while True:
            maintenant = time.monotonic()
            for nom, periode, fn in TACHES:
                if maintenant - derniere[nom] >= periode:
                    derniere[nom] = maintenant
                    try:
                        fn()
                    except Exception:
                        log.exception("Tâche planifiée en erreur : %s", nom)
            time.sleep(5)

    threading.Thread(target=boucle, name="badgeo-planificateur", daemon=True).start()
