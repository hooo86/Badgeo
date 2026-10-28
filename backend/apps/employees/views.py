from rest_framework import viewsets

from apps.accounts.permissions import ALL, ScopedQuerysetMixin
from apps.audit.utils import AuditMixin

from .models import Employee
from .serializers import EmployeeSerializer


class EmployeeViewSet(AuditMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    role_rules = {"read": ALL, "write": {"sysadmin", "hr_manager", "hr_staff"}}
    search_fields = ["matricule", "first_name", "last_name", "job_title"]
    filterset_fields = ["status", "org_unit"]
