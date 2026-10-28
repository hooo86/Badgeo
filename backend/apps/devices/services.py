import logging
import socket

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import PunchEvent
from apps.employees.models import DeviceUserMap

from .adapters import DeviceError, get_adapter
from .models import Device, SyncLog

log = logging.getLogger(__name__)
BATCH = 1000


def diagnose(device) -> dict:
    """Layered diagnostic: TCP reachability first, then protocol handshake."""
    result = {"tcp_reachable": False, "handshake": False, "stage": None, "message": "", "info": {}}
    try:
        socket.create_connection((device.ip_address, device.port), timeout=5).close()
        result["tcp_reachable"] = True
    except OSError as e:
        if device.protocol == "zk_tcp":
            result.update(stage="network", message=f"{device.ip_address}:{device.port} unreachable: {e}")
            _mark(device, Device.Status.DISCONNECTED, result["message"])
            return result
    try:
        result["info"] = {k: str(v) for k, v in get_adapter(device).test().items()}
        result["handshake"] = True
        _mark(device, Device.Status.CONNECTED)
        if result["info"].get("serial_number") and not device.serial_number:
            device.serial_number = result["info"]["serial_number"]
            device.save(update_fields=["serial_number"])
    except DeviceError as e:
        result.update(stage=e.stage, message=str(e))
        _mark(device, Device.Status.ERROR if e.stage != "network" else Device.Status.DISCONNECTED, str(e))
    return result


def _mark(device, status, error=""):
    device.status, device.last_error = status, error
    if status == Device.Status.CONNECTED:
        device.last_seen_at = timezone.now()
    device.save(update_fields=["status", "last_error", "last_seen_at"])


def sync_device(device, trigger=SyncLog.Trigger.AUTO) -> SyncLog:
    """Pull every punch from the device and insert the new ones.

    The device memory is never cleared, and inserts are idempotent
    (unique device/user/timestamp), so a failed or repeated sync loses nothing."""
    log_row = SyncLog.objects.create(device=device, trigger=trigger)
    try:
        raw = list(get_adapter(device).fetch_punches())
        tz = timezone.get_current_timezone()
        maps = dict(DeviceUserMap.objects.filter(device=device).values_list("device_user_id", "employee_id"))
        before = PunchEvent.objects.filter(device=device).count()
        with transaction.atomic():
            for i in range(0, len(raw), BATCH):
                PunchEvent.objects.bulk_create([
                    PunchEvent(device=device, device_user_id=p.device_user_id,
                               employee_id=maps.get(p.device_user_id),
                               timestamp=timezone.make_aware(p.timestamp, tz) if timezone.is_naive(p.timestamp) else p.timestamp,
                               punch_type=p.punch_type, verify_mode=p.verify_mode)
                    for p in raw[i:i + BATCH]], ignore_conflicts=True)
        total = PunchEvent.objects.filter(device=device).count()
        log_row.fetched, log_row.created, log_row.success = len(raw), total - before, True
        device.events_total, device.last_sync_ok, device.consecutive_failures = total, True, 0
        device.last_sync_at = timezone.now()
        _mark(device, Device.Status.CONNECTED)
    except DeviceError as e:
        log_row.success, log_row.error = False, str(e)
        device.last_sync_ok = False
        device.consecutive_failures += 1
        device.save(update_fields=["last_sync_ok", "consecutive_failures"])
        _mark(device, Device.Status.DISCONNECTED if e.stage == "network" else Device.Status.ERROR, str(e))
        log.warning("sync failed for %s: %s", device, e)
    finally:
        log_row.finished_at = timezone.now()
        log_row.save()
        device.save(update_fields=["events_total", "last_sync_at"])
    return log_row
