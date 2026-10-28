from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import LoginView, UserViewSet
from apps.attendance.views import PunchEventViewSet
from apps.devices.views import DeviceViewSet, SyncLogViewSet
from apps.audit.views import AuditLogViewSet
from apps.employees.views import EmployeeViewSet
from apps.orgs.views import OrgUnitViewSet

router = DefaultRouter()
router.register("devices", DeviceViewSet)
router.register("sync-logs", SyncLogViewSet)
router.register("employees", EmployeeViewSet)
router.register("punches", PunchEventViewSet)
router.register("org-units", OrgUnitViewSet)
router.register("users", UserViewSet)
router.register("audit-logs", AuditLogViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/auth/token/", LoginView.as_view()),
    path("api-auth/", include("rest_framework.urls")),
]
