from .models import AuditLog

SENSITIVE = ("password", "comm_key", "token", "secret")


def _clean(data, exclude=()):
    if data is None:
        return None
    return {k: v for k, v in dict(data).items()
            if k not in exclude and not any(s in k for s in SENSITIVE)}


def audit(request, action, obj=None, before=None, after=None, detail=None, user=None, exclude=()):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    u = user or (request.user if request.user.is_authenticated else None)
    return AuditLog.objects.create(
        user=u, action=action,
        object_type=obj._meta.label if obj is not None else "",
        object_id=str(obj.pk) if obj is not None and obj.pk else "",
        before=_clean(before, exclude), after=_clean(after, exclude), detail=detail,
        ip=xff or request.META.get("REMOTE_ADDR") or None)


class AuditMixin:
    """Logs create/update/delete (secrets stripped) on a ModelViewSet."""
    audit_exclude = ()

    def perform_create(self, serializer):
        super().perform_create(serializer)
        audit(self.request, "create", serializer.instance, after=serializer.data, exclude=self.audit_exclude)

    def perform_update(self, serializer):
        before = self.get_serializer(serializer.instance).data
        super().perform_update(serializer)
        audit(self.request, "update", serializer.instance, before=before, after=serializer.data,
              exclude=self.audit_exclude)

    def perform_destroy(self, instance):
        before = self.get_serializer(instance).data
        pk = instance.pk
        super().perform_destroy(instance)
        instance.pk = pk
        audit(self.request, "delete", instance, before=before, exclude=self.audit_exclude)
