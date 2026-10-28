"""Premier démarrage de l'édition locale : crée le compte administrateur avec un mot de passe aléatoire.

Le mot de passe est écrit UNE fois dans <données>/identifiants-initiaux.txt ; il doit être changé à la première connexion."""
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.models import Profile, Role


class Command(BaseCommand):
    help = "Crée l'administrateur initial s'il n'existe aucun compte."

    def handle(self, *a, **o):
        if User.objects.exists():
            return
        mdp = secrets.token_urlsafe(9)
        u = User.objects.create_superuser("admin", password=mdp)
        Profile.objects.create(user=u, role=Role.SYSADMIN, must_change_password=True)
        f = settings.DONNEES / "identifiants-initiaux.txt" if hasattr(settings, "DONNEES") else None
        texte = f"Badgeo – identifiants initiaux\nUtilisateur : admin\nMot de passe : {mdp}\nChangez-le dès la première connexion, puis supprimez ce fichier.\n"
        if f:
            f.write_text(texte, encoding="utf-8")
        self.stdout.write(texte)
