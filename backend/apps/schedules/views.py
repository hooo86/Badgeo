from rest_framework import viewsets

from apps.accounts.permissions import ALL
from apps.audit.utils import AuditMixin

from .models import Holiday, Rotation, Shift, ShiftAssignment
from .serializers import AssignmentSerializer, HolidaySerializer, RotationSerializer, ShiftSerializer

RULES = {"read": ALL, "write": {"sysadmin", "hr_manager"}}


class ShiftViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset, serializer_class, role_rules = Shift.objects.all(), ShiftSerializer, RULES


class RotationViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset, serializer_class, role_rules = Rotation.objects.all(), RotationSerializer, RULES


class AssignmentViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = ShiftAssignment.objects.select_related("shift", "rotation", "employee", "org_unit")
    serializer_class, role_rules = AssignmentSerializer, RULES
    filterset_fields = ["employee", "org_unit", "shift"]


class HolidayViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset, serializer_class, role_rules = Holiday.objects.all(), HolidaySerializer, RULES
