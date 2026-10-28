from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import models


def minutes_between(start: time, end: time) -> int:
    """Minutes from start to end, wrapping past midnight when end <= start."""
    s, e = start.hour * 60 + start.minute, end.hour * 60 + end.minute
    return (e - s) % (24 * 60) or 24 * 60


class Shift(models.Model):
    """A working-time template. end_time <= start_time means the shift crosses midnight."""
    class Kind(models.TextChoices):
        FIXED = "fixed", "Fixe"
        FLEXIBLE = "flexible", "Variable"
        NIGHT = "night", "Nuit"

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.FIXED)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=60, help_text="Pause théorique déduite du temps de travail")
    late_grace_minutes = models.PositiveIntegerField(default=5, help_text="Tolérance de retard")
    early_leave_grace_minutes = models.PositiveIntegerField(default=0)
    earliest_in = models.TimeField(null=True, blank=True, help_text="Heure minimale d'arrivée")
    latest_in = models.TimeField(null=True, blank=True, help_text="Heure maximale d'arrivée (horaire variable)")
    theoretical_minutes = models.PositiveIntegerField(null=True, blank=True,
                                                      help_text="Durée de travail théorique ; défaut = amplitude - pause")
    overtime_threshold_minutes = models.PositiveIntegerField(default=30)
    work_days = models.JSONField(default=list, help_text="Jours travaillés, 0=lundi … 6=dimanche")

    def clean(self):
        if self.kind == self.Kind.FLEXIBLE and not self.latest_in:
            raise ValidationError("Un horaire variable exige une heure maximale d'arrivée.")
        if any(d not in range(7) for d in self.work_days):
            raise ValidationError("work_days doit contenir des entiers de 0 à 6.")

    @property
    def crosses_midnight(self) -> bool:
        return self.end_time <= self.start_time

    @property
    def expected_minutes(self) -> int:
        if self.theoretical_minutes is not None:
            return self.theoretical_minutes
        return max(0, minutes_between(self.start_time, self.end_time) - self.break_minutes)

    def works_on(self, d: date) -> bool:
        return d.weekday() in self.work_days

    def __str__(self):
        return self.name


class Rotation(models.Model):
    """Repeating cycle of shifts (None = rest day), e.g. [matin, soir, nuit, repos]."""
    name = models.CharField(max_length=100, unique=True)
    anchor_date = models.DateField(help_text="Jour correspondant à la première case du cycle")
    cycle = models.JSONField(help_text="Liste d'identifiants de Shift ou null (repos)")

    def shift_id_on(self, d: date):
        if not self.cycle:
            return None
        return self.cycle[(d - self.anchor_date).days % len(self.cycle)]


class ShiftAssignment(models.Model):
    """Assigns a shift (or rotation) to an employee or an org unit for a validity period."""
    employee = models.ForeignKey("employees.Employee", null=True, blank=True, on_delete=models.CASCADE,
                                 related_name="shift_assignments")
    org_unit = models.ForeignKey("orgs.OrgUnit", null=True, blank=True, on_delete=models.CASCADE,
                                 related_name="shift_assignments")
    shift = models.ForeignKey(Shift, null=True, blank=True, on_delete=models.PROTECT, related_name="assignments")
    rotation = models.ForeignKey(Rotation, null=True, blank=True, on_delete=models.PROTECT, related_name="assignments")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valid_from"]

    def clean(self):
        if bool(self.employee) == bool(self.org_unit):
            raise ValidationError("Cibler un employé OU une unité organisationnelle.")
        if bool(self.shift) == bool(self.rotation):
            raise ValidationError("Choisir un horaire OU une rotation.")
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError("valid_to précède valid_from.")


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)
    recurring = models.BooleanField(default=False, help_text="Se répète chaque année (même jour/mois)")

    class Meta:
        ordering = ["date"]
