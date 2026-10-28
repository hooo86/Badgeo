from rest_framework import viewsets

from apps.accounts.permissions import ALL
from apps.audit.utils import AuditMixin

from .models import OrgUnit
from .serializers import OrgUnitSerializer


class OrgUnitViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = OrgUnit.objects.all()
    serializer_class = OrgUnitSerializer
    role_rules = {"read": ALL, "write": {"sysadmin", "hr_manager"}}
    filterset_fields = ["kind", "parent"]
