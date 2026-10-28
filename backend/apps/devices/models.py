import uuid

from django.db import models

from apps.core.crypto import decrypt, encrypt


class Device(models.Model):
    class Vendor(models.TextChoices):
        ZKTECO = "zkteco", "ZKTeco"
        UNIS = "unis", "UNIS"

    class Protocol(models.TextChoices):
        ZK_TCP = "zk_tcp", "ZK TCP (port 4370)"
        ZK_UDP = "zk_udp", "ZK UDP"

    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Inconnu"
        CONNECTED = "connected", "Connecté"
        DISCONNECTED = "disconnected", "Déconnecté"
        ERROR = "error", "Erreur"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    vendor = models.CharField(max_length=16, choices=Vendor.choices)
    model = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField(default=4370)
    serial_number = models.CharField(max_length=64, blank=True)
    protocol = models.CharField(max_length=16, choices=Protocol.choices, default=Protocol.ZK_TCP)
    comm_key_enc = models.TextField(blank=True, editable=False, help_text="Encrypted communication key")
    timezone = models.CharField(max_length=64, default="Africa/Algiers", help_text="Fuseau de l'horloge de l'appareil")
    enabled = models.BooleanField(default=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNKNOWN)
    last_error = models.TextField(blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_ok = models.BooleanField(null=True)
    events_total = models.PositiveBigIntegerField(default=0)
    sync_interval_minutes = models.PositiveIntegerField(default=5, help_text="0 disables automatic sync")
    consecutive_failures = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["ip_address", "port"], name="uniq_device_endpoint")]

    @property
    def comm_key(self) -> int:
        v = decrypt(self.comm_key_enc)
        return int(v) if v else 0

    @comm_key.setter
    def comm_key(self, value):
        self.comm_key_enc = encrypt(str(value)) if value else ""

    def __str__(self):
        return self.name


class SyncLog(models.Model):
    class Trigger(models.TextChoices):
        MANUAL = "manual"
        AUTO = "auto"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sync_logs")
    trigger = models.CharField(max_length=8, choices=Trigger.choices, default=Trigger.AUTO)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(null=True)
    fetched = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
