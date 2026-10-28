from collections import Counter
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasStaffRole
from rest_framework.response import Response

from apps.accounts.models import GLOBAL_ROLES, get_role
from apps.attendance.models import AttendanceDay, PunchEvent
from apps.attendance.services import local_naive
from apps.corrections.models import Correction
from apps.devices.models import Device
from apps.employees.models import Employee
from apps.orgs.models import OrgUnit

PRESENT = ("present", "in_progress", "incomplete")
ANOMALY_STATUSES = ("incomplete", "no_punch")


def scoped_employees(user):
    qs = Employee.objects.filter(status="active")
    if get_role(user) in GLOBAL_ROLES:
        return qs
    return qs.filter(org_unit__in=OrgUnit.with_descendants(user.profile.scopes.values_list("id", flat=True)))


def top_unit(unit):
    """Root-most ancestor below the structure = the 'direction' used for grouping."""
    chain = []
    while unit:
        chain.append(unit)
        unit = unit.parent
    return chain[-2] if len(chain) > 1 else (chain[0] if chain else None)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasStaffRole])
def summary(request):
    """Real figures only, computed from AttendanceDay / PunchEvent / Device for the requesting user's scope."""
    today = timezone.localdate()
    emps = scoped_employees(request.user)
    ids = list(emps.values_list("id", flat=True))
    days = AttendanceDay.objects.filter(employee_id__in=ids, work_date=today)
    present = days.filter(status__in=PRESENT)
    expected = days.exclude(status__in=("rest", "holiday", "scheduled"))
    out = {
        "date": today.isoformat(),
        "headcount": len(ids),
        "present": present.count(),
        "late": days.filter(late_min__gt=0).count(),
        "absent": days.filter(status__in=("absent", "no_punch", "leave", "sick", "mission", "permission")).count(),
        "on_leave": days.filter(status__in=("leave", "sick", "mission", "permission")).count(),
        "incomplete": days.filter(status="incomplete").count(),
        "anomalies_to_review": AttendanceDay.objects.filter(employee_id__in=ids, status__in=ANOMALY_STATUSES,
                                                            work_date__lt=today).count(),
        "corrections_pending": Correction.objects.filter(employee_id__in=ids, state="pending").count(),
        "punches_today": PunchEvent.objects.filter(employee_id__in=ids, timestamp__date=today).count(),
        "presence_rate": round(100 * present.count() / expected.count(), 1) if expected.count() else None,
    }
    if get_role(request.user) in GLOBAL_ROLES:
        devs = Device.objects.filter(enabled=True)
        out["devices"] = {"connected": devs.filter(status="connected").count(),
                          "disconnected": devs.exclude(status="connected").count(),
                          "last_sync_at": max((d.last_sync_at for d in devs if d.last_sync_at), default=None)}
        out["unmapped_punches_today"] = PunchEvent.objects.filter(employee__isnull=True, timestamp__date=today).count()
    # arrivals curve (15-minute buckets of first entry)
    buckets = Counter()
    for fi in present.exclude(first_in=None).values_list("first_in", flat=True):
        t = local_naive(fi)
        buckets[f"{t.hour:02d}:{t.minute // 15 * 15:02d}"] += 1
    out["arrivals"] = [{"slot": k, "count": v} for k, v in sorted(buckets.items())]
    # last 14 days
    start = today - timedelta(days=13)
    per_day = AttendanceDay.objects.filter(employee_id__in=ids, work_date__gte=start).values("work_date").annotate(
        present=Count("id", filter=Q(status__in=PRESENT)),
        late=Count("id", filter=Q(late_min__gt=0)),
        expected=Count("id", filter=~Q(status__in=("rest", "holiday", "scheduled", "pending"))))
    out["daily"] = [{"date": r["work_date"].isoformat(), "present": r["present"], "late": r["late"], "expected": r["expected"]}
                    for r in sorted(per_day, key=lambda r: r["work_date"])]
    # presence rate by direction
    rates = {}
    for d in days.select_related("employee__org_unit__parent__parent"):
        u = top_unit(d.employee.org_unit)
        name = u.name if u else "Sans affectation"
        r = rates.setdefault(name, [0, 0])
        if d.status not in ("rest", "holiday", "scheduled"):
            r[1] += 1
            r[0] += d.status in PRESENT
    out["by_unit"] = [{"unit": k, "present": a, "expected": b, "rate": round(100 * a / b, 1) if b else None}
                      for k, (a, b) in sorted(rates.items())]
    # live feed
    feed = PunchEvent.objects.filter(employee_id__in=ids).select_related("employee", "device").order_by("-timestamp")[:8]
    out["recent"] = [{"time": timezone.localtime(p.timestamp).isoformat(timespec="seconds"),
                      "employee": f"{p.employee.first_name} {p.employee.last_name}", "matricule": p.employee.matricule,
                      "source": p.get_source_display(), "device": p.device.name if p.device else None} for p in feed]
    return Response(out)
