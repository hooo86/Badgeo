from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.accounts.models import get_role
from apps.accounts.permissions import ALL, ScopedQuerysetMixin
from apps.attendance.services import link_punches
from apps.audit.utils import AuditMixin, audit

from . import io as eio
from .models import DeviceUserMap, Employee
from .serializers import DeviceUserMapSerializer, EmployeeSerializer

HR_WRITE = {"sysadmin", "hr_manager", "hr_staff"}


class EmployeeViewSet(AuditMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("org_unit")
    serializer_class = EmployeeSerializer
    role_rules = {"read": ALL, "write": HR_WRITE}
    search_fields = ["matricule", "first_name", "last_name", "job_title"]
    filterset_fields = ["status", "org_unit"]

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser], url_path="import")
    def import_file(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "Fichier manquant (champ 'file')."}, status=400)
        result = eio.import_employees(f, dry_run=request.query_params.get("dry_run") == "1")
        audit(request, "employees_import", detail={k: result[k] for k in ("created", "updated", "dry_run")} | {"errors": len(result["errors"])})
        return Response(result)

    @action(detail=False, methods=["get"], url_path="export")
    def export_file(self, request):
        if get_role(request.user) not in HR_WRITE:
            return Response({"detail": "Export réservé aux profils RH."}, status=403)
        xlsx = request.query_params.get("fmt") == "xlsx"
        audit(request, "employees_export", detail={"fmt": "xlsx" if xlsx else "csv"})
        body = eio.export_xlsx() if xlsx else eio.export_csv()
        ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if xlsx else "text/csv; charset=utf-8"
        r = HttpResponse(body, content_type=ctype)
        r["Content-Disposition"] = f'attachment; filename="personnel.{"xlsx" if xlsx else "csv"}"'
        return r


class DeviceUserMapViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = DeviceUserMap.objects.select_related("employee", "device")
    serializer_class = DeviceUserMapSerializer
    role_rules = {"read": {"sysadmin", "device_admin", "hr_manager", "hr_staff"}, "write": HR_WRITE | {"device_admin"}}
    filterset_fields = ["employee", "device"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        m = serializer.instance
        link_punches(m.employee, m.device, m.device_user_id)
