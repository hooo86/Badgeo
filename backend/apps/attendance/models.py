import uuid

from django.db import models


class PunchEvent(models.Model):
    """One raw punch. Never edited or deleted by the application.
    source=device: pulled from a terminal (deduplicated on device/user/timestamp);
    source=mobile: self-punch from the mobile app; source=manual: created by a validated correction."""
    class Source(models.TextChoices):
        DEVICE = "device", "Pointeuse"
        MOBILE = "mobile", "Application mobile"
        MANUAL = "manual", "Correction validée"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.DEVICE)
    device = models.ForeignKey("devices.Device", null=True, blank=True, on_delete=models.PROTECT, related_name="punches")
    device_user_id = models.CharField(max_length=32, blank=True)
    native_id = models.CharField(max_length=64, blank=True, help_text="Identifiant natif de l'événement si fourni")
    employee = models.ForeignKey("employees.Employee", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="punches")
    timestamp = models.DateTimeField(db_index=True)
    punch_type = models.SmallIntegerField(default=0, help_text="0 entrée, 1 sortie, 2 pause out, 3 pause in, 4 HS in, 5 HS out")
    verify_mode = models.SmallIntegerField(default=0, help_text="1 empreinte, 15 visage, 3 badge, 0 code")
    created_at = models.DateTimeField(auto_now_add=True)  # retrieval date

    class Meta:
        ordering = ["-timestamp"]
        constraints = [models.UniqueConstraint(fields=["device", "device_user_id", "timestamp"],
                                               name="uniq_punch_per_device")]
        indexes = [models.Index(fields=["employee", "timestamp"])]


class AttendanceDay(models.Model):
    """Derived, recomputable daily result. Raw punches are the source of truth."""
    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="days")
    work_date = models.DateField(db_index=True)
    shift = models.ForeignKey("schedules.Shift", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    computed_status = models.CharField(max_length=16)
    override_status = models.CharField(max_length=16, blank=True, help_text="Posé par une correction validée")
    status = models.CharField(max_length=16, db_index=True)
    justified = models.BooleanField(null=True)
    first_in = models.DateTimeField(null=True, blank=True)
    last_out = models.DateTimeField(null=True, blank=True)
    punch_count = models.PositiveSmallIntegerField(default=0)
    presence_min = models.PositiveIntegerField(null=True, blank=True)
    worked_min = models.PositiveIntegerField(null=True, blank=True)
    late_min = models.PositiveIntegerField(default=0)
    early_leave_min = models.PositiveIntegerField(default=0)
    overtime_min = models.PositiveIntegerField(default=0)
    missing_min = models.PositiveIntegerField(default=0)
    anomalies = models.JSONField(default=list)
    punch_times = models.JSONField(default=list, help_text="Pointages retenus (ISO, heure locale)")
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-work_date", "employee__last_name"]
        constraints = [models.UniqueConstraint(fields=["employee", "work_date"], name="uniq_day_per_employee")]
