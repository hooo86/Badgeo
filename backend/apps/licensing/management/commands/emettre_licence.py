"""Fabrique une clé d'activation (poste de l'éditeur, avec BADGEO_LICENCE_CLE_PRIVEE dans l'environnement)."""
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.licensing.licence import MODULES, LicenceInvalide, signer


class Command(BaseCommand):
    help = "Émet une clé d'activation pour un poste (code BDG-XXXX-XXXX-XXXX) ou, en essai, pour tous les postes (« * »)."

    def add_arguments(self, p):
        p.add_argument("code", help="Code d'installation du poste, ou * pour une clé d'essai")
        p.add_argument("--client", required=True)
        p.add_argument("--modules", default=",".join(sorted(MODULES)), help=f"parmi {sorted(MODULES)} (séparés par des virgules)")
        p.add_argument("--employes", type=int, help="plafond d'employés actifs (absent = illimité)")
        p.add_argument("--pointeuses", type=int, help="plafond de pointeuses (absent = illimité)")
        g = p.add_mutually_exclusive_group()
        g.add_argument("--jours", type=int, help="durée en jours à partir d'aujourd'hui")
        g.add_argument("--jusqu-au", help="date de fin AAAA-MM-JJ")

    def handle(self, code, client, modules, employes, pointeuses, jours, jusqu_au=None, **o):
        fin = timezone.localdate() + timedelta(days=jours) if jours else (date.fromisoformat(o["jusqu_au"]) if o.get("jusqu_au") else None)
        try:
            cle = signer(code, client, [m for m in modules.split(",") if m], employes, pointeuses, fin)
        except LicenceInvalide as e:
            raise CommandError(str(e))
        self.stdout.write(cle)
