"""Dépannage : remet le compte « admin » à admin / Badgeo@2026 (mot de passe provisoire) quand on est bloqué dehors.

Exige un accès à l'ordinateur (commande locale) ; l'action est notée dans le journal d'audit."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from apps.accounts.models import Profile, Role
from apps.audit.models import AuditLog

from .initialiser_local import IDENTIFIANT, MOT_DE_PASSE


class Command(BaseCommand):
    help = "Réinitialise le compte administrateur par défaut."

    def handle(self, *a, **o):
        u, _ = User.objects.get_or_create(username=IDENTIFIANT)
        u.is_active = u.is_superuser = u.is_staff = True
        u.set_password(MOT_DE_PASSE)
        u.save()
        Token.objects.filter(user=u).delete()
        Profile.objects.update_or_create(user=u, defaults={"role": Role.SYSADMIN, "must_change_password": True})
        AuditLog.objects.create(user=None, action="admin_reinitialise", detail={"via": "commande locale"})
        self.stdout.write(f"Compte réinitialisé : {IDENTIFIANT} / {MOT_DE_PASSE} (à changer à la connexion)")
