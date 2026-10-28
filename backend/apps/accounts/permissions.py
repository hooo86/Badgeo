from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.orgs.models import OrgUnit

from .models import GLOBAL_ROLES, get_role

ALL = {"sysadmin", "device_admin", "hr_manager", "hr_staff", "dept_head", "viewer"}


class RolePermission(BasePermission):
    """View declares `role_rules = {"read": {...}, "write": {...}}`; undeclared => sysadmin only."""
    def has_permission(self, request, view):
        role = get_role(request.user)
        if role is None:
            return False
        rules = getattr(view, "role_rules", {"read": {"sysadmin"}, "write": {"sysadmin"}})
        kind = "read" if request.method in SAFE_METHODS else "write"
        return role in rules.get(kind, set())


class ScopedQuerysetMixin:
    """Restricts rows to the user's org-unit scope for non-global roles (no scope => nothing)."""
    scope_field = "org_unit"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if get_role(user) in GLOBAL_ROLES:
            return qs
        units = OrgUnit.with_descendants(user.profile.scopes.values_list("id", flat=True))
        return qs.filter(**{f"{self.scope_field}__in": units})
