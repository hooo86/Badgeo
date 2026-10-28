"""Licences Badgeo.

- Le « code d'installation » dépend du poste : copier l'installation ailleurs invalide la clé.
- La « clé d'activation » est un document signé (Ed25519) par l'éditeur : client, modules, plafonds (employés actifs,
  pointeuses), date de fin et code d'installation. Seule la clé publique est dans le logiciel ; vérification hors ligne.
- Une clé d'essai (code « * ») vaut pour n'importe quel poste : réservée aux versions de test, toujours datée.
"""
import base64
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from django.utils import timezone

PREFIXE = "BADG1-"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I : se dicte au téléphone
TOUS_POSTES = "*"
MODULES = {"mobile": "Application mobile employé", "reports": "Rapports et exports", "leaves": "Absences et autorisations"}


class LicenceInvalide(ValueError):
    pass


def _identifiant_machine():
    if os.environ.get("BADGEO_EMPREINTE"):
        return os.environ["BADGEO_EMPREINTE"]
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as cle:
                return winreg.QueryValueEx(cle, "MachineGuid")[0]
        except OSError:
            pass
    for chemin in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(chemin) as f:
                valeur = f.read().strip()
            if valeur:
                return valeur
        except OSError:
            pass
    return f"mac-{uuid.getnode():012x}"


def code_installation():
    """Code à 12 caractères lisibles, ex. BDG-7K3F-92QX-M4LD."""
    n = int.from_bytes(hashlib.sha256(f"badgeo-licence:{_identifiant_machine()}".encode()).digest()[:8], "big")
    lettres = []
    for _ in range(12):
        n, r = divmod(n, len(ALPHABET))
        lettres.append(ALPHABET[r])
    s = "".join(lettres)
    return f"BDG-{s[:4]}-{s[4:8]}-{s[8:]}"


def normaliser_code(code):
    if (code or "").strip() == TOUS_POSTES:
        return TOUS_POSTES
    s = re.sub(r"[^A-Z0-9]", "", (code or "").upper())
    if s.startswith("BDG"):
        s = s[3:]
    if len(s) != 12 or any(c not in ALPHABET for c in s):
        raise LicenceInvalide("Code d'installation incorrect : il a la forme BDG-XXXX-XXXX-XXXX.")
    return f"BDG-{s[:4]}-{s[4:8]}-{s[8:]}"


@dataclass
class InfosLicence:
    numero: str
    code: str
    client: str
    max_employes: int | None
    max_pointeuses: int | None
    modules: list = field(default_factory=list)
    expire_le: date | None = None
    emise_le: date | None = None

    @property
    def essai(self):
        return self.code == TOUS_POSTES

    def expiree(self, jour=None):
        return bool(self.expire_le and (jour or jour_de_reference()) > self.expire_le)

    def jours_restants(self, jour=None):
        return (self.expire_le - (jour or jour_de_reference())).days if self.expire_le else None

    def a_module(self, nom):
        return nom in self.modules


def _b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _deb64(texte):
    return base64.urlsafe_b64decode(texte + "=" * (-len(texte) % 4))


def generer_paire_de_cles():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    privee = Ed25519PrivateKey.generate()
    brut = privee.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    publique = privee.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return _b64(brut), _b64(publique)


def cle_publique_configuree():
    from .cle_publique import CLE_PUBLIQUE

    return getattr(settings, "BADGEO_LICENCE_CLE_PUBLIQUE", "") or CLE_PUBLIQUE


def signer(code, client, modules, max_employes=None, max_pointeuses=None, expire_le=None, cle_privee=None):
    """Fabrique une clé d'activation (côté éditeur uniquement)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    cle_privee = cle_privee or os.environ.get("BADGEO_LICENCE_CLE_PRIVEE", "")
    if not cle_privee:
        raise LicenceInvalide("Clé privée de l'éditeur absente (variable BADGEO_LICENCE_CLE_PRIVEE).")
    code = normaliser_code(code)
    if code == TOUS_POSTES and not expire_le:
        raise LicenceInvalide("Une clé d'essai (tous postes) doit avoir une date de fin.")
    inconnus = set(modules) - set(MODULES)
    if inconnus:
        raise LicenceInvalide(f"Modules inconnus : {sorted(inconnus)}. Disponibles : {sorted(MODULES)}.")
    contenu = {"v": 1, "n": uuid.uuid4().hex[:10].upper(), "c": code, "cl": client[:120],
               "e": int(max_employes) if max_employes else None, "p": int(max_pointeuses) if max_pointeuses else None,
               "m": sorted(set(modules)), "x": expire_le.isoformat() if expire_le else None,
               "d": timezone.localdate().isoformat()}
    donnees = json.dumps(contenu, separators=(",", ":"), ensure_ascii=False).encode()
    signature = Ed25519PrivateKey.from_private_bytes(_deb64(cle_privee)).sign(donnees)
    return PREFIXE + _b64(donnees) + "." + _b64(signature)


def verifier(cle, code=None, cle_publique=None):
    """Vérifie signature et poste ; renvoie InfosLicence ou lève LicenceInvalide."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    cle_publique = cle_publique or cle_publique_configuree()
    if not cle_publique:
        raise LicenceInvalide("Ce logiciel n'a pas de clé de vérification : contactez l'éditeur.")
    cle = re.sub(r"\s+", "", cle or "")
    if not cle.startswith(PREFIXE) or "." not in cle:
        raise LicenceInvalide("Clé d'activation incorrecte : vérifiez qu'elle a été copiée en entier.")
    try:
        partie, signature = cle[len(PREFIXE):].split(".", 1)
        donnees = _deb64(partie)
        Ed25519PublicKey.from_public_bytes(_deb64(cle_publique)).verify(_deb64(signature), donnees)
        c = json.loads(donnees)
        infos = InfosLicence(numero=c["n"], code=c["c"], client=c["cl"], max_employes=c.get("e"), max_pointeuses=c.get("p"),
                             modules=list(c.get("m") or []), expire_le=date.fromisoformat(c["x"]) if c.get("x") else None,
                             emise_le=date.fromisoformat(c["d"]))
    except (InvalidSignature, ValueError, TypeError, KeyError):
        raise LicenceInvalide("Clé d'activation non valable : elle n'a pas été délivrée par l'éditeur ou a été modifiée.")
    if code and not infos.essai and infos.code != code:
        raise LicenceInvalide(f"Cette clé a été délivrée pour un autre poste ({infos.code}). "
                              f"Le code de ce poste est {code} : demandez une clé pour ce code.")
    return infos


def licence_requise():
    return getattr(settings, "BADGEO_LICENCE_REQUISE", False)


_CACHE = {}


def licence_active():
    """Licence enregistrée et valable pour CE poste, ou None (mise en cache jusqu'au changement)."""
    from .models import Licence

    obj = Licence.objects.first()
    if obj is None:
        return None
    code = _CACHE.get("code") or _CACHE.setdefault("code", code_installation())
    marque = (obj.pk, obj.cle, code, cle_publique_configuree())
    if _CACHE.get("marque") != marque:
        try:
            _CACHE["infos"] = verifier(obj.cle, code)
        except LicenceInvalide:
            _CACHE["infos"] = None
        _CACHE["marque"] = marque
    return _CACHE["infos"]


def jour_de_reference():
    """Plus récente des dates : celle du poste et la dernière déjà vue. Reculer l'horloge ne prolonge pas une licence."""
    from django.db.models import Max

    from .models import Licence

    aujourdhui = timezone.localdate()
    vue = _CACHE.get("vue")
    if vue is None:
        vue = Licence.objects.aggregate(m=Max("derniere_date"))["m"] or date.min
        _CACHE["vue"] = vue
    if aujourdhui > vue:
        Licence.objects.update(derniere_date=aujourdhui)
        _CACHE["vue"] = vue = aujourdhui
    return vue


def horloge_reculee():
    return jour_de_reference() > timezone.localdate()


def vider_cache():
    _CACHE.clear()
