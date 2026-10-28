"""Plafonds de la licence, appliqués quel que soit le chemin de création (API, import, admin)."""
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.devices.models import Device
from apps.employees.models import Employee

from .licence import licence_active, licence_requise


def _plafond(champ):
    if not licence_requise():
        return None
    lic = licence_active()
    return getattr(lic, champ, None) if lic else 0


@receiver(pre_save, sender=Employee)
def plafond_employes(sender, instance, **kw):
    if instance.pk or instance.status != "active":
        return
    limite = _plafond("max_employes")
    if limite is not None and Employee.objects.filter(status="active").count() >= limite:
        raise ValidationError(f"Plafond de la licence atteint : {limite} employé(s) actif(s). Contactez l'éditeur pour l'augmenter.")


@receiver(pre_save, sender=Device)
def plafond_pointeuses(sender, instance, **kw):
    if instance.pk:
        return
    limite = _plafond("max_pointeuses")
    if limite is not None and Device.objects.count() >= limite:
        raise ValidationError(f"Plafond de la licence atteint : {limite} pointeuse(s). Contactez l'éditeur pour l'augmenter.")
