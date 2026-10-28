from datetime import date

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ALL, ScopedQuerysetMixin
from apps.audit.utils import audit
from apps.employees.models import Employee

from .models import AttendanceDay, PunchEvent
from .serializers import AttendanceDaySerializer, PunchEventSerializer
from .services import recompute_range


class PunchEventViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PunchEvent.objects.select_related("device", "employee")
    serializer_class = PunchEventSerializer
    role_rules = {"read": ALL}
    scope_field = "employee__org_unit"
    filterset_fields = {"device": ["exact"], "employee": ["exact"], "source": ["exact"], "timestamp": ["gte", "lte"]}
    search_fields = ["device_user_id", "employee__matricule", "employee__last_name"]
    ordering_fields = ["timestamp"]


class AttendanceDayViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AttendanceDay.objects.select_related("employee", "shift")
    serializer_class = AttendanceDaySerializer
    scope_field = "employee__org_unit"
    role_rules = {"read": ALL, "write": {"sysadmin", "hr_manager", "hr_staff"}}
    filterset_fields = {"employee": ["exact"], "employee__org_unit": ["exact"], "status": ["exact", "in"],
                        "work_date": ["exact", "gte", "lte"]}
    search_fields = ["employee__matricule", "employee__last_name", "employee__first_name"]
    ordering_fields = ["work_date", "late_min", "overtime_min", "employee__last_name"]

    @action(detail=False, methods=["post"])
    def recompute(self, request):
        """Rebuild derived days from raw punches for a period (e.g. after changing a shift)."""
        start, end = date.fromisoformat(request.data["from"]), date.fromisoformat(request.data["to"])
        if (end - start).days > 92:
            return Response({"detail": "Période limitée à 92 jours."}, status=400)
        emps = Employee.objects.filter(status="active")
        n = recompute_range(emps, start, end)
        audit(request, "recompute", detail={"from": str(start), "to": str(end), "days": n})
        return Response({"days": n})
