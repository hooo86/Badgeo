"""Premier démarrage de l'édition locale : crée le compte administrateur par défaut (admin / Badgeo@2026).

Le mot de passe est connu (documenté) : il est donc PROVISOIRE, le changement est exigé dès la première connexion
et aucune autre action n'est possible avant."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.models import Profile, Role

IDENTIFIANT = "admin"
MOT_DE_PASSE = "Badgeo@2026"


class Command(BaseCommand):
    help = "Crée l'administrateur par défaut s'il n'existe aucun compte."

    def handle(self, *a, **o):
        if User.objects.exists():
            return
        u = User.objects.create_superuser(IDENTIFIANT, password=MOT_DE_PASSE)
        Profile.objects.create(user=u, role=Role.SYSADMIN, must_change_password=True)
        self.stdout.write(f"Compte créé : {IDENTIFIANT} / {MOT_DE_PASSE} (à changer à la première connexion)")
