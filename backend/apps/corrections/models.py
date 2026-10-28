from django.conf import settings
from django.db import models


class Correction(models.Model):
    """A requested change to a day's result. Raw punches are never touched: a validated correction adds a
    manual punch (source=manual) or sets a status override, then the day is recomputed."""
    class Kind(models.TextChoices):
        ADD_PUNCH = "add_punch", "Ajouter un pointage"
        SET_STATUS = "set_status", "Forcer le statut"

    class State(models.TextChoices):
        PENDING = "pending", "En attente"
        VALIDATED = "validated", "Validée"
        REJECTED = "rejected", "Rejetée"

    employee = models.ForeignKey("employees.Employee", on_delete=models.PROTECT, related_name="corrections")
    work_date = models.DateField()
    kind = models.CharField(max_length=12, choices=Kind.choices)
    new_timestamp = models.DateTimeField(null=True, blank=True)
    new_status = models.CharField(max_length=16, blank=True)
    initial = models.JSONField(help_text="Valeurs de la journée avant correction")
    reason = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    result_punch = models.ForeignKey("attendance.PunchEvent", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    after = models.JSONField(null=True, blank=True, help_text="Valeurs de la journée après validation")

    class Meta:
        ordering = ["-created_at"]
