from django.core.exceptions import ValidationError
from django.db import models


class Leave(models.Model):
    class Kind(models.TextChoices):
        LEAVE = "leave", "Congé"
        PERMISSION = "permission", "Permission / sortie autorisée"
        MISSION = "mission", "Mission"
        SICK = "sick", "Arrêt maladie"
        REST = "rest", "Repos exceptionnel"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="leaves")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True, help_text="Permission partielle uniquement")
    end_time = models.TimeField(null=True, blank=True)
    justified = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("end_date précède start_date.")
        if (self.start_time or self.end_time) and (self.kind != self.Kind.PERMISSION or self.start_date != self.end_date
                                                   or not (self.start_time and self.end_time)):
            raise ValidationError("Les heures ne valent que pour une permission d'un seul jour (début et fin).")
