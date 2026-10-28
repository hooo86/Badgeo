from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ALL
from apps.audit.utils import AuditMixin, audit

from .models import Device, SyncLog
from .serializers import DeviceSerializer, SyncLogSerializer
from .services import diagnose
from .tasks import sync_device_task


class DeviceViewSet(AuditMixin, viewsets.ModelViewSet):
    role_rules = {"read": {"sysadmin", "device_admin", "hr_manager", "hr_staff"},
                  "write": {"sysadmin", "device_admin"}}
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    search_fields = ["name", "ip_address", "serial_number", "model"]
    filterset_fields = ["vendor", "status", "enabled"]

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        device = self.get_object()
        result = diagnose(device)
        audit(request, "device_test", device, detail={"ok": result["handshake"], "stage": result["stage"]})
        return Response(result)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        device = self.get_object()
        audit(request, "device_sync", device)
        sync_device_task.delay(device.pk, SyncLog.Trigger.MANUAL)
        return Response({"queued": True}, status=202)


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    role_rules = {"read": {"sysadmin", "device_admin", "hr_manager", "hr_staff"}}
    queryset = SyncLog.objects.select_related("device")
    serializer_class = SyncLogSerializer
    filterset_fields = ["device", "success", "trigger"]
