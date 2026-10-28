"""Crée la paire de clés qui signe les licences (à faire UNE fois, par l'éditeur)."""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.licensing.licence import generer_paire_de_cles

FICHIER = Path(__file__).resolve().parents[2] / "cle_publique.py"


class Command(BaseCommand):
    help = "Écrit la clé publique dans apps/licensing/cle_publique.py et affiche la clé privée (à garder hors de Git)."

    def add_arguments(self, parser):
        parser.add_argument("--remplacer", action="store_true",
                            help="Remplace une clé existante : toutes les licences déjà délivrées deviennent invalides.")

    def handle(self, remplacer=False, **options):
        texte = FICHIER.read_text(encoding="utf-8")
        if 'CLE_PUBLIQUE = ""' not in texte and not remplacer:
            raise CommandError("Une clé publique existe déjà. --remplacer seulement si la clé privée est perdue ou divulguée.")
        privee, publique = generer_paire_de_cles()
        FICHIER.write_text(texte.split("CLE_PUBLIQUE =")[0] + f'CLE_PUBLIQUE = "{publique}"\n', encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Clé publique écrite : committez apps/licensing/cle_publique.py"))
        self.stdout.write("\nGardez cette clé PRIVÉE en lieu sûr (jamais dans Git) :\n")
        self.stdout.write(f"BADGEO_LICENCE_CLE_PRIVEE={privee}\n")
