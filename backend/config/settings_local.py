"""Édition locale Windows : un seul poste, SQLite, Waitress, licence obligatoire, tâches planifiées dans le processus.

Les données vivent hors du dossier du programme (C:\\ProgramData\\Badgeo ou BADGEO_DONNEES) : une mise à jour
ou une désinstallation ne les efface jamais."""
import os
import secrets
from pathlib import Path

from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR

if os.environ.get("BADGEO_DONNEES"):
    DONNEES = Path(os.environ["BADGEO_DONNEES"])
elif os.name == "nt":
    DONNEES = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Badgeo"
else:
    DONNEES = Path.home() / ".badgeo"
DONNEES.mkdir(parents=True, exist_ok=True)


def _secret(nom, fabriquer):
    """Secret généré au premier démarrage et conservé dans le dossier des données."""
    f = DONNEES / nom
    if not f.exists():
        f.write_text(fabriquer(), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


SECRET_KEY = _secret("secret_key.txt", lambda: secrets.token_urlsafe(64))
# Clé qui protège les secrets des pointeuses : la perdre rend les clés de communication illisibles (la sauvegarder !)
os.environ.setdefault("DEVICE_SECRET_KEY", _secret("cle_secrets_pointeuses.txt", lambda: __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()))

DEBUG = False
ALLOWED_HOSTS = ["*"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DONNEES / "badgeo.sqlite3",
                         "OPTIONS": {"timeout": 30, "init_command": "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;"}}}
BACKUP_DIR = Path(os.environ.get("BADGEO_BACKUP_DIR", DONNEES / "sauvegardes"))
LOG_DIR = DONNEES / "journaux"
LOG_DIR.mkdir(exist_ok=True)

BADGEO_LICENCE_REQUISE = os.environ.get("BADGEO_LICENCE_REQUISE", "1") == "1"
CELERY_TASK_ALWAYS_EAGER = True          # pas de Redis : les tâches s'exécutent sur place
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BEAT_SCHEDULE = {}                # remplacé par apps.core.scheduler (thread du lanceur)

# Interface React servie par Django (WhiteNoise) : / → index.html
FRONTEND = BASE_DIR / "frontend_dist"
if FRONTEND.exists():
    WHITENOISE_ROOT = FRONTEND
    WHITENOISE_INDEX_FILE = True
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}

# Connexion en HTTP sur le réseau local
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_PROXY_SSL_HEADER = None

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"},
                 "fichier": {"class": "logging.handlers.RotatingFileHandler", "filename": str(LOG_DIR / "badgeo.log"),
                             "maxBytes": 5_000_000, "backupCount": 5, "encoding": "utf-8", "formatter": "std"}},
    "root": {"handlers": ["console", "fichier"], "level": "INFO"},
}
