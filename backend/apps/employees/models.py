import uuid

from django.db import models


class Employee(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    matricule = models.CharField(max_length=32, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    org_unit = models.ForeignKey("orgs.OrgUnit", null=True, blank=True, on_delete=models.PROTECT, related_name="employees")
    job_title = models.CharField(max_length=150, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, default="active", choices=[("active", "Actif"), ("suspended", "Suspendu"), ("left", "Sorti")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.matricule} {self.last_name} {self.first_name}"


class DeviceUserMap(models.Model):
    """Links the user id stored on a terminal to an Employee (one employee can be on several devices)."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="device_ids")
    device = models.ForeignKey("devices.Device", on_delete=models.CASCADE, related_name="user_maps")
    device_user_id = models.CharField(max_length=32)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["device", "device_user_id"], name="uniq_device_user")]
