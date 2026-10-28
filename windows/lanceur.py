"""Point d'entrée de Badgeo pour Windows (console ou service « Badgeo »).

À chaque démarrage : copie de sécurité de la base avant migration si une mise à jour est en attente, migrations,
première initialisation (administrateur), planificateur (synchronisation des pointeuses, recalcul, sauvegardes),
puis serveur web Waitress.

    lanceur.py                    démarre Badgeo
    lanceur.py commande <args>    lance une commande d'administration (ex. : seed_demo, emettre_licence, check)
"""
import logging
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent / "app"
sys.path.insert(0, str(RACINE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_local")
journal = logging.getLogger("badgeo.lanceur")


def preparer():
    import shutil
    from datetime import datetime

    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executeur = MigrationExecutor(connection)
    en_attente = executeur.migration_plan(executeur.loader.graph.leaf_nodes())
    base = Path(settings.DATABASES["default"]["NAME"])
    if en_attente and base.exists():
        try:  # mise à jour : copie de la base avant de la modifier (les 5 dernières sont gardées)
            dossier = Path(settings.BACKUP_DIR) / "avant-mise-a-jour"
            dossier.mkdir(parents=True, exist_ok=True)
            copie = dossier / f"badgeo_{datetime.now():%Y-%m-%d_%H%M%S}.sqlite3"
            shutil.copy2(base, copie)
            for ancienne in sorted(dossier.glob("badgeo_*.sqlite3"))[:-5]:
                ancienne.unlink(missing_ok=True)
            journal.warning("Copie de sécurité avant mise à jour : %s", copie)
        except Exception:
            journal.exception("Copie de sécurité avant mise à jour impossible")
    call_command("migrate", interactive=False, verbosity=0)
    call_command("initialiser_local")


def servir():
    from waitress import serve

    from apps.core import scheduler
    from config.wsgi import application

    port = int(os.environ.get("BADGEO_PORT", "8000"))
    scheduler.demarrer()
    journal.warning("Badgeo démarré : http://localhost:%s", port)
    serve(application, host="0.0.0.0", port=port, threads=8, max_request_body_size=2 * 1024 ** 3, ident="Badgeo",
          clear_untrusted_proxy_headers=True)


def main():
    import django

    django.setup()
    if len(sys.argv) > 2 and sys.argv[1] == "commande":
        from django.core.management import execute_from_command_line

        execute_from_command_line(["badgeo"] + sys.argv[2:])
        return
    preparer()
    servir()


if __name__ == "__main__":
    main()
