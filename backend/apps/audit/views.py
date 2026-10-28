from rest_framework import serializers, viewsets

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    role_rules = {"read": {"sysadmin", "hr_manager"}}
    filterset_fields = ["action", "user", "object_type"]
