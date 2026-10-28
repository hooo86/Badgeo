from rest_framework import viewsets

from apps.accounts.permissions import ALL, ScopedQuerysetMixin

from .models import PunchEvent
from .serializers import PunchEventSerializer


class PunchEventViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    role_rules = {"read": ALL}
    scope_field = "employee__org_unit"
    queryset = PunchEvent.objects.select_related("device", "employee")
    serializer_class = PunchEventSerializer
    filterset_fields = {"device": ["exact"], "employee": ["exact"], "timestamp": ["gte", "lte"]}
    search_fields = ["device_user_id", "employee__matricule", "employee__last_name"]
    ordering_fields = ["timestamp"]
