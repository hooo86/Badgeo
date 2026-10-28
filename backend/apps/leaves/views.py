from rest_framework import viewsets

from apps.accounts.permissions import ALL, ScopedQuerysetMixin
from apps.attendance.services import recompute_range
from apps.audit.utils import AuditMixin

from .models import Leave
from .serializers import LeaveSerializer


class LeaveViewSet(AuditMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Leave.objects.select_related("employee")
    serializer_class = LeaveSerializer
    scope_field = "employee__org_unit"
    role_rules = {"read": ALL, "write": {"sysadmin", "hr_manager", "hr_staff"}}
    filterset_fields = {"employee": ["exact"], "kind": ["exact"], "start_date": ["gte", "lte"], "end_date": ["gte", "lte"]}

    def _refresh(self, leave):
        recompute_range([leave.employee], leave.start_date, leave.end_date)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._refresh(serializer.instance)

    def perform_update(self, serializer):
        old = (serializer.instance.start_date, serializer.instance.end_date)
        super().perform_update(serializer)
        recompute_range([serializer.instance.employee], min(old[0], serializer.instance.start_date),
                        max(old[1], serializer.instance.end_date))

    def perform_destroy(self, instance):
        emp, s, e = instance.employee, instance.start_date, instance.end_date
        super().perform_destroy(instance)
        recompute_range([emp], s, e)
