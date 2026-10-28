from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import get_role
from apps.accounts.permissions import ScopedQuerysetMixin
from apps.audit.utils import audit

from . import services
from .models import Correction
from .serializers import CorrectionSerializer

REVIEWERS = {"sysadmin", "hr_manager"}
HR = {"sysadmin", "hr_manager", "hr_staff"}


class CorrectionViewSet(ScopedQuerysetMixin, mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Create / read only: a correction is never edited or deleted, only validated or rejected."""
    queryset = Correction.objects.select_related("employee", "created_by", "reviewed_by")
    serializer_class = CorrectionSerializer
    scope_field = "employee__org_unit"
    role_rules = {"read": HR | {"dept_head", "viewer"}, "write": HR}
    filterset_fields = ["state", "employee", "kind", "work_date"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        audit(self.request, "correction_create", serializer.instance, after=serializer.data)

    def _review(self, request, fn, **kw):
        c = self.get_object()
        try:
            fn(c, request.user, **kw)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=403)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        audit(request, f"correction_{c.state}", c, detail={"note": c.review_note})
        return Response(self.get_serializer(c).data)

    def _require_reviewer(self, request):
        if get_role(request.user) not in REVIEWERS:
            return Response({"detail": "Validation réservée au responsable RH."}, status=403)

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        return self._require_reviewer(request) or self._review(request, services.validate,
                                                               note=request.data.get("note", ""))

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._require_reviewer(request) or self._review(request, services.reject,
                                                               note=request.data.get("note", ""))
