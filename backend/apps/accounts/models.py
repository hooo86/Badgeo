from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    SYSADMIN = "sysadmin", "Administrateur système"
    DEVICE_ADMIN = "device_admin", "Administrateur des pointeuses"
    HR_MANAGER = "hr_manager", "Responsable RH"
    HR_STAFF = "hr_staff", "Gestionnaire RH"
    DEPT_HEAD = "dept_head", "Responsable de direction"
    VIEWER = "viewer", "Utilisateur en consultation"


GLOBAL_ROLES = {Role.SYSADMIN, Role.DEVICE_ADMIN, Role.HR_MANAGER, Role.HR_STAFF}


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)
    scopes = models.ManyToManyField("orgs.OrgUnit", blank=True,
                                    help_text="Périmètre (directions/services) pour les rôles non globaux")


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return Role.SYSADMIN
    profile = getattr(user, "profile", None)
    return profile.role if profile else None
