import uuid

from django.db import models


class PunchEvent(models.Model):
    """One raw punch pulled from a terminal. Immutable; deduplicated on (device, user, timestamp)."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    device = models.ForeignKey("devices.Device", on_delete=models.PROTECT, related_name="punches")
    device_user_id = models.CharField(max_length=32)
    employee = models.ForeignKey("employees.Employee", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="punches")
    timestamp = models.DateTimeField(db_index=True)
    punch_type = models.SmallIntegerField(default=0, help_text="0 in, 1 out, 2 break out, 3 break in, 4 OT in, 5 OT out")
    verify_mode = models.SmallIntegerField(default=0, help_text="1 fingerprint, 15 face, 3 card, 0 password...")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        constraints = [models.UniqueConstraint(fields=["device", "device_user_id", "timestamp"],
                                               name="uniq_punch_per_device")]
