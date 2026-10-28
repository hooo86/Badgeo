from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import LoginView, UserViewSet
from apps.attendance.views import PunchEventViewSet
from apps.devices.views import DeviceViewSet, SyncLogViewSet
from apps.audit.views import AuditLogViewSet
from apps.attendance.views import AttendanceDayViewSet
from apps.corrections.views import CorrectionViewSet
from apps.employees.views import DeviceUserMapViewSet, EmployeeViewSet
from apps.leaves.views import LeaveViewSet
from apps.me import views as me_views
from apps.reports import dashboard, views as report_views
from apps.schedules.views import AssignmentViewSet, HolidayViewSet, RotationViewSet, ShiftViewSet
from apps.orgs.views import OrgUnitViewSet

router = DefaultRouter()
router.register("devices", DeviceViewSet)
router.register("sync-logs", SyncLogViewSet)
router.register("employees", EmployeeViewSet)
router.register("punches", PunchEventViewSet)
router.register("org-units", OrgUnitViewSet)
router.register("users", UserViewSet)
router.register("audit-logs", AuditLogViewSet)
router.register("attendance-days", AttendanceDayViewSet)
router.register("device-users", DeviceUserMapViewSet)
router.register("shifts", ShiftViewSet)
router.register("rotations", RotationViewSet)
router.register("shift-assignments", AssignmentViewSet)
router.register("holidays", HolidayViewSet)
router.register("leaves", LeaveViewSet)
router.register("corrections", CorrectionViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/me/", me_views.me),
    path("api/me/punch/", me_views.punch),
    path("api/me/history/", me_views.history),
    path("api/me/planning/", me_views.planning),
    path("api/dashboard/", dashboard.summary),
    path("api/reports/<str:name_>/", report_views.report),
    path("api/", include(router.urls)),
    path("api/auth/token/", LoginView.as_view()),
    path("api-auth/", include("rest_framework.urls")),
]
