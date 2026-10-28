"""Sauvegarde / restauration applicative, indépendante du moteur de base (SQLite ou PostgreSQL).

Fichier .badgeo = archive zip { manifest.json, data.json } ; chiffrée (Fernet + scrypt) si une phrase de passe est
configurée. Exclus : sessions, jetons, permissions, journal d'administration Django, la licence (restaurer une
sauvegarde ne doit ni déconnecter la licence ni la remplacer) et le journal d'audit (jamais remonté dans le temps). La mémoire des pointeuses n'est jamais touchée.
"""
import base64
import hashlib
import io
import json
import logging
import os
import re
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone

log = logging.getLogger(__name__)

FORMAT = 1
MAGIC = b"BADGEOENC1"
EXCLUS = ["contenttypes", "sessions", "auth.permission", "admin.logentry", "licensing", "authtoken", "audit"]
NOM = re.compile(r"^badgeo_\d{8}_\d{6}(_\d+)?_(manual|auto|pre_restore|imported)\.badgeo$")
PAR_DEFAUT = {"auto": True, "hour": 2, "keep": 14, "copy_dir": ""}
CONFIRMATION = "RESTAURER"


class SauvegardeError(Exception):
    pass


def dossier() -> Path:
    d = Path(settings.BACKUP_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def reglages() -> dict:
    f = dossier() / "reglages.json"
    try:
        return {**PAR_DEFAUT, **json.loads(f.read_text("utf-8"))}
    except (OSError, ValueError):
        return dict(PAR_DEFAUT)


def enregistrer_reglages(data: dict) -> dict:
    cur = reglages()
    if "auto" in data:
        cur["auto"] = bool(data["auto"])
    if "hour" in data:
        if not 0 <= int(data["hour"]) <= 23:
            raise SauvegardeError("L'heure doit être comprise entre 0 et 23.")
        cur["hour"] = int(data["hour"])
    if "keep" in data:
        if not 1 <= int(data["keep"]) <= 365:
            raise SauvegardeError("Le nombre de sauvegardes à conserver doit être compris entre 1 et 365.")
        cur["keep"] = int(data["keep"])
    if "copy_dir" in data:
        cible = str(data["copy_dir"]).strip()
        if cible:
            p = Path(cible)
            try:
                p.mkdir(parents=True, exist_ok=True)
                (p / ".badgeo-test").write_text("ok")
                (p / ".badgeo-test").unlink()
            except OSError as e:
                raise SauvegardeError(f"Dossier de copie inutilisable : {e}")
        cur["copy_dir"] = cible
    (dossier() / "reglages.json").write_text(json.dumps(cur, indent=2), "utf-8")
    return cur


# --- chiffrement -----------------------------------------------------------------------------------------------
def _fernet(passphrase: str, salt: bytes):
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    cle = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(passphrase.encode())
    return Fernet(base64.urlsafe_b64encode(cle))


def _chiffrer(octets: bytes, passphrase: str) -> bytes:
    salt = os.urandom(16)
    return MAGIC + salt + _fernet(passphrase, salt).encrypt(octets)


def _dechiffrer(octets: bytes, passphrase: str) -> bytes:
    from cryptography.fernet import InvalidToken

    if not passphrase:
        raise SauvegardeError("Cette sauvegarde est chiffrée : la phrase de passe (BADGEO_BACKUP_PASSPHRASE) est requise.")
    try:
        return _fernet(passphrase, octets[len(MAGIC):len(MAGIC) + 16]).decrypt(octets[len(MAGIC) + 16:])
    except InvalidToken:
        raise SauvegardeError("Phrase de passe incorrecte ou fichier altéré.")


def _ouvrir(chemin: Path, passphrase: str) -> zipfile.ZipFile:
    brut = chemin.read_bytes()
    if brut.startswith(MAGIC):
        brut = _dechiffrer(brut, passphrase)
    try:
        return zipfile.ZipFile(io.BytesIO(brut))
    except zipfile.BadZipFile:
        raise SauvegardeError("Fichier de sauvegarde illisible.")


# --- création ---------------------------------------------------------------------------------------------------
def _migrations() -> list:
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    return sorted(f"{a}.{n}" for a, n in loader.applied_migrations if a not in ("admin", "contenttypes", "sessions", "auth", "authtoken"))


def creer(kind="manual", utilisateur="", passphrase=None) -> dict:
    passphrase = settings.BACKUP_PASSPHRASE if passphrase is None else passphrase
    tampon = io.StringIO()
    with transaction.atomic():  # lecture cohérente
        call_command("dumpdata", natural_foreign=True, natural_primary=True, exclude=EXCLUS, stdout=tampon)
    data = tampon.getvalue().encode("utf-8")
    comptes = {}
    for ligne in json.loads(data):
        comptes[ligne["model"]] = comptes.get(ligne["model"], 0) + 1
    manifeste = {"format": FORMAT, "creee_le": timezone.now().isoformat(), "type": kind, "par": utilisateur,
                 "migrations": _migrations(), "lignes": comptes, "sha256": hashlib.sha256(data).hexdigest()}
    zone = io.BytesIO()
    with zipfile.ZipFile(zone, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifeste, indent=1))
        z.writestr("data.json", data)
    contenu = _chiffrer(zone.getvalue(), passphrase) if passphrase else zone.getvalue()
    base = f"badgeo_{timezone.localtime():%Y%m%d_%H%M%S}"
    nom, i = f"{base}_{kind}.badgeo", 1
    while (dossier() / nom).exists():
        nom, i = f"{base}_{i}_{kind}.badgeo", i + 1
    chemin = dossier() / nom
    tmp = chemin.with_suffix(".part")
    tmp.write_bytes(contenu)
    tmp.replace(chemin)  # écriture atomique : jamais de fichier à moitié écrit dans la liste
    meta = {"nom": nom, "type": kind, "creee_le": manifeste["creee_le"], "par": utilisateur, "taille": len(contenu),
            "chiffree": bool(passphrase), "lignes": sum(comptes.values()), "copie": ""}
    cible = reglages().get("copy_dir")
    if cible:
        try:
            shutil.copy2(chemin, Path(cible) / nom)
            meta["copie"] = str(Path(cible) / nom)
        except OSError as e:
            meta["copie"] = f"ÉCHEC : {e}"
            log.error("Copie de la sauvegarde vers %s impossible : %s", cible, e)
    chemin.with_suffix(".json").write_text(json.dumps(meta), "utf-8")
    return meta


def lister() -> list:
    out = []
    for f in sorted(dossier().glob("badgeo_*.badgeo"), reverse=True):
        meta = f.with_suffix(".json")
        try:
            m = json.loads(meta.read_text("utf-8"))
        except (OSError, ValueError):
            m = {"nom": f.name, "type": NOM.match(f.name) and f.name.rsplit("_", 1)[-1][:-7] or "?", "par": "",
                 "creee_le": datetime.fromtimestamp(f.stat().st_mtime, timezone.get_current_timezone()).isoformat(),
                 "chiffree": f.read_bytes()[:len(MAGIC)] == MAGIC, "lignes": None, "copie": ""}
        m["taille"] = f.stat().st_size
        out.append(m)
    return sorted(out, key=lambda m: m["creee_le"], reverse=True)


def chemin_de(nom: str) -> Path:
    if not NOM.match(nom):
        raise SauvegardeError("Nom de sauvegarde invalide.")
    p = dossier() / nom
    if not p.exists():
        raise SauvegardeError("Sauvegarde introuvable.")
    return p


def supprimer(nom: str):
    p = chemin_de(nom)
    p.unlink()
    p.with_suffix(".json").unlink(missing_ok=True)


def appliquer_retention():
    """Garde les N dernières sauvegardes automatiques (réglage) et les 5 dernières « avant restauration »."""
    cfg = reglages()
    for kind, garder in (("auto", cfg["keep"]), ("pre_restore", 5)):
        for m in [x for x in lister() if x["type"] == kind][garder:]:
            supprimer(m["nom"])


def sauvegarde_planifiee(now=None):
    """À appeler régulièrement : crée la sauvegarde automatique du jour quand l'heure réglée est passée."""
    cfg = reglages()
    now = timezone.localtime(now)
    if not cfg["auto"] or now.hour < cfg["hour"]:
        return None
    deja = any(m["type"] == "auto" and timezone.localtime(datetime.fromisoformat(m["creee_le"])).date() == now.date() for m in lister())
    if deja:
        return None
    meta = creer("auto", "planification")
    appliquer_retention()
    return meta


# --- restauration ----------------------------------------------------------------------------------------------
def verifier(chemin: Path, passphrase=None) -> dict:
    """Contrôle intégrité et compatibilité sans rien modifier. Renvoie le manifeste."""
    passphrase = settings.BACKUP_PASSPHRASE if passphrase is None else passphrase
    with _ouvrir(chemin, passphrase) as z:
        try:
            man = json.loads(z.read("manifest.json"))
            data = z.read("data.json")
        except KeyError:
            raise SauvegardeError("Fichier de sauvegarde incomplet.")
    if man.get("format") != FORMAT:
        raise SauvegardeError("Format de sauvegarde non pris en charge.")
    if hashlib.sha256(data).hexdigest() != man["sha256"]:
        raise SauvegardeError("Sauvegarde corrompue (somme de contrôle différente).")
    inconnues = set(man["migrations"]) - set(_migrations())
    if inconnues:
        raise SauvegardeError("Cette sauvegarde vient d'une version plus récente de Badgeo : mettez le logiciel à jour avant de la restaurer.")
    man["_data"] = data
    return man


def restaurer(nom: str, utilisateur="", passphrase=None) -> dict:
    """Remplace TOUTES les données par celles de la sauvegarde. Une sauvegarde « avant restauration » est créée d'abord ;
    tout est fait dans une transaction : en cas d'erreur, la base reste telle qu'elle était."""
    from django.contrib.auth.models import User

    from apps.audit.models import AuditLog
    from apps.licensing.models import Licence

    chemin = chemin_de(nom)
    man = verifier(chemin, passphrase)
    avant = creer("pre_restore", utilisateur)
    licences = list(Licence.objects.values())
    audits = list(AuditLog.objects.values())  # conservés tels quels : l'historique ne se rembobine pas
    fichier = Path(settings.BACKUP_DIR) / ".restauration.json"
    fichier.write_bytes(man.pop("_data"))
    try:
        with transaction.atomic():
            call_command("flush", interactive=False, verbosity=0)
            call_command("loaddata", str(fichier), verbosity=0)
            for l in licences:
                Licence.objects.create(**l)
            utilisateurs = set(User.objects.values_list("pk", flat=True))
            for a in audits:  # un auteur absent des données restaurées est noté dans le détail au lieu d'être perdu
                if a["user_id"] is not None and a["user_id"] not in utilisateurs:
                    a["detail"] = {**(a["detail"] or {}), "utilisateur_id_supprime": a["user_id"]}
                    a["user_id"] = None
            AuditLog.objects.bulk_create([AuditLog(**a) for a in audits])
    except Exception as e:
        log.exception("Restauration échouée")
        raise SauvegardeError(f"Restauration impossible, aucune donnée modifiée : {e}")
    finally:
        fichier.unlink(missing_ok=True)
    appliquer_retention()
    return {"restauree": nom, "sauvegarde_avant": avant["nom"], "creee_le": man["creee_le"]}


def importer(contenu: bytes, passphrase=None) -> dict:
    """Ajoute un fichier .badgeo fourni par l'utilisateur à la liste (après contrôle) ; ne restaure pas."""
    base = f"badgeo_{timezone.localtime():%Y%m%d_%H%M%S}"
    chemin = dossier() / f"{base}_imported.badgeo"
    i = 1
    while chemin.exists():
        chemin = dossier() / f"{base}_{i}_imported.badgeo"
        i += 1
    chemin.write_bytes(contenu)
    try:
        man = verifier(chemin, passphrase)
    except SauvegardeError:
        chemin.unlink(missing_ok=True)
        raise
    meta = {"nom": chemin.name, "type": "imported", "creee_le": man["creee_le"], "par": man.get("par", ""),
            "taille": len(contenu), "chiffree": contenu[:len(MAGIC)] == MAGIC, "lignes": sum(man["lignes"].values()), "copie": ""}
    chemin.with_suffix(".json").write_text(json.dumps(meta), "utf-8")
    return meta
