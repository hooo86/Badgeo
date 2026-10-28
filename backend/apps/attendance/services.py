import logging
from datetime import date, datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.employees.models import Employee
from apps.leaves.models import Leave
from apps.schedules.services import is_holiday, shift_for

from . import engine
from .models import AttendanceDay, PunchEvent

log = logging.getLogger(__name__)


def to_spec(shift):
    if shift is None:
        return None
    return engine.ShiftSpec(
        start=shift.start_time, end=shift.end_time, break_min=shift.break_minutes,
        late_grace=shift.late_grace_minutes, early_grace=shift.early_leave_grace_minutes,
        expected_min=shift.expected_minutes, overtime_threshold=shift.overtime_threshold_minutes,
        earliest_in=shift.earliest_in, latest_in=shift.latest_in,
        flexible=shift.kind == "flexible", work_days=tuple(shift.work_days))


def local_naive(ts):
    return timezone.localtime(ts).replace(tzinfo=None) if timezone.is_aware(ts) else ts


def work_date_for(employee, ts_local: datetime, cache: dict) -> date:
    """A punch just after midnight belongs to the previous day when that day's shift crosses midnight."""
    d = ts_local.date()
    prev = d - timedelta(days=1)
    if prev not in cache:
        cache[prev] = shift_for(employee, prev)
    s = cache[prev]
    if s and s.crosses_midnight and s.works_on(prev) and \
            ts_local <= datetime.combine(d, s.end_time) + engine.TRAIL:
        return prev
    return d


def punches_of_day(employee, d: date, cache=None):
    cache = {} if cache is None else cache
    lo = timezone.make_aware(datetime.combine(d, datetime.min.time()))
    hi = lo + timedelta(days=2)
    out = []
    for p in PunchEvent.objects.filter(employee=employee, timestamp__gte=lo, timestamp__lt=hi).values_list("timestamp", flat=True):
        t = local_naive(p)
        if work_date_for(employee, t, cache) == d:
            out.append(t)
    return out


def leave_for(employee, d: date):
    rows = list(Leave.objects.filter(employee=employee, start_date__lte=d, end_date__gte=d))
    if not rows:
        return None
    rows.sort(key=lambda l: l.start_time is not None)  # full-day entries win over partial permissions
    l = rows[0]
    return engine.LeaveSpec(kind=l.kind, justified=l.justified, start=l.start_time, end=l.end_time)


def recompute_day(employee, d: date, now=None) -> AttendanceDay:
    now = now or timezone.localtime().replace(tzinfo=None)
    cache = {}
    shift = shift_for(employee, d)
    res = engine.compute_day(
        d, punches_of_day(employee, d, cache), to_spec(shift), holiday=is_holiday(d),
        leave=leave_for(employee, d), now=now,
        dedup_minutes=getattr(settings, "PUNCH_DEDUP_MINUTES", 2),
        no_punch_is_absent=getattr(settings, "NO_PUNCH_BECOMES_ABSENCE", False))
    aware = lambda t: timezone.make_aware(t) if t else None
    existing = AttendanceDay.objects.filter(employee=employee, work_date=d).first()
    override = existing.override_status if existing else ""
    day, _ = AttendanceDay.objects.update_or_create(employee=employee, work_date=d, defaults=dict(
        shift=shift, computed_status=res.status, override_status=override, status=override or res.status,
        justified=res.justified, first_in=aware(res.first_in), last_out=aware(res.last_out),
        punch_count=len(res.punches), presence_min=res.presence_min, worked_min=res.worked_min,
        late_min=res.late_min, early_leave_min=res.early_leave_min, overtime_min=res.overtime_min,
        missing_min=res.missing_min, anomalies=res.anomalies,
        punch_times=[t.isoformat(timespec="minutes") for t in res.punches]))
    return day


def recompute_range(employees, start: date, end: date):
    n = 0
    for emp in employees:
        d = start
        while d <= end:
            recompute_day(emp, d)
            d += timedelta(days=1)
            n += 1
    return n


def recompute_recent(employees=None, days: int = 2):
    today = timezone.localdate()
    emps = employees if employees is not None else Employee.objects.filter(status="active")
    return recompute_range(emps, today - timedelta(days=days - 1), today)


def link_punches(employee, device, device_user_id) -> int:
    """Backfill employee on already-synced raw punches once a device user is mapped (raw rows keep their data)."""
    return PunchEvent.objects.filter(device=device, device_user_id=device_user_id, employee__isnull=True
                                     ).update(employee=employee)
