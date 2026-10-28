"""Vendor-independent attendance computation. Pure functions on naive local datetimes: no DB, no timezone.

Rules (also documented in docs/REGLES_PRESENCE.md):
- Punches closer than `dedup_minutes` to the previous kept one are ignored (anomaly duplicate_punch).
- Lateness: if arrival exceeds scheduled start + grace, the full delay from scheduled start is counted; else 0.
  Flexible shifts: delay beyond `latest_in` (+grace) only.
- Early leave: shortfall to scheduled end, if above the early-leave grace.
- Presence = last - first punch; worked = sum of in/out pairs with >=4 punches, else presence - theoretical break.
- Overtime is only *potential*: time after scheduled end (or beyond theoretical duration), above the threshold.
- A workday without punch is `no_punch` (not absence) unless `no_punch_is_absent` is configured and the day is closed.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional

MISSING_OUT, MISSING_IN, ODD, DUP = "missing_out", "missing_in", "odd_punches", "duplicate_punch"
LONG_PRESENCE_MIN = 16 * 60
TRAIL = timedelta(hours=4)


@dataclass(frozen=True)
class ShiftSpec:
    start: time
    end: time
    break_min: int = 0
    late_grace: int = 0
    early_grace: int = 0
    expected_min: int = 480
    overtime_threshold: int = 30
    earliest_in: Optional[time] = None
    latest_in: Optional[time] = None
    flexible: bool = False
    work_days: tuple = (0, 1, 2, 3, 4)

    @property
    def crosses_midnight(self):
        return self.end <= self.start


@dataclass(frozen=True)
class LeaveSpec:
    kind: str  # leave | permission | mission | sick | rest
    justified: bool = True
    start: Optional[time] = None  # partial permission window
    end: Optional[time] = None

    @property
    def partial(self):
        return self.start is not None and self.end is not None


@dataclass
class DayResult:
    work_date: date
    status: str
    justified: Optional[bool] = None
    first_in: Optional[datetime] = None
    last_out: Optional[datetime] = None
    punches: list = field(default_factory=list)
    presence_min: Optional[int] = None
    worked_min: Optional[int] = None
    late_min: int = 0
    early_leave_min: int = 0
    overtime_min: int = 0
    missing_min: int = 0
    anomalies: list = field(default_factory=list)


def _mins(delta: timedelta) -> int:
    return int(delta.total_seconds() // 60)


def expected_window(d: date, s: ShiftSpec):
    start = datetime.combine(d, s.start)
    end = datetime.combine(d + timedelta(days=1 if s.crosses_midnight else 0), s.end)
    return start, end


def dedupe(punches, minutes):
    kept, dup = [], False
    for p in sorted(punches):
        if kept and p - kept[-1] < timedelta(minutes=minutes):
            dup = True
            continue
        kept.append(p)
    return kept, dup


def compute_day(work_date: date, punches, shift: Optional[ShiftSpec], holiday: bool = False,
                leave: Optional[LeaveSpec] = None, now: Optional[datetime] = None,
                dedup_minutes: int = 2, no_punch_is_absent: bool = False) -> DayResult:
    res = DayResult(work_date, "")
    pts, had_dup = dedupe(punches, dedup_minutes)
    res.punches = pts
    if had_dup:
        res.anomalies.append(DUP)
    if pts:
        res.first_in, res.last_out = pts[0], (pts[-1] if len(pts) > 1 else None)
        res.presence_min = _mins(pts[-1] - pts[0]) if len(pts) > 1 else None

    full_leave = leave is not None and not leave.partial
    if full_leave:
        res.status, res.justified = leave.kind, leave.justified
        if pts:
            res.anomalies.append("punch_during_leave")
        return res

    if shift is None:
        res.status = "present" if pts else "rest"
        if pts:
            res.anomalies.append("no_shift")
        return res

    if holiday or work_date.weekday() not in shift.work_days:
        res.status = "holiday" if holiday else "rest"
        if pts:
            res.status = "present"
            res.anomalies.append("punch_on_holiday" if holiday else "punch_on_rest_day")
            if len(pts) > 1:
                res.worked_min = res.presence_min
                res.overtime_min = res.presence_min or 0
        return res

    exp_start, exp_end = expected_window(work_date, shift)
    open_window = now is not None and now < exp_end + TRAIL

    if not pts:
        if now is not None and now < exp_end + TRAIL and work_date >= now.date() - timedelta(days=1):
            res.status = "pending" if now < exp_end else "no_punch"
        else:
            res.status = "no_punch"
        if res.status == "no_punch" and no_punch_is_absent and not open_window:
            res.status = "absent"
        if work_date > (now.date() if now else work_date):
            res.status = "scheduled"
        return res

    n = len(pts)
    if n == 1:
        p = pts[0]
        if open_window and work_date <= now.date() and p <= now:
            res.status = "in_progress"
            return res
        if p > exp_start + (exp_end - exp_start) / 2:
            res.first_in, res.last_out = None, p
            res.anomalies.append(MISSING_IN)
        else:
            res.anomalies.append(MISSING_OUT)
        res.status = "incomplete"
    elif n % 2 == 1:
        res.anomalies.append(ODD)
        res.status = "in_progress" if open_window and work_date <= now.date() else "incomplete"
        if res.status == "incomplete":
            res.last_out = None
    else:
        res.status = "present"

    complete = res.status == "present"
    first, last = res.first_in, res.last_out

    # permission window (partial) covering the start or end of the day
    perm_s = perm_e = None
    if leave is not None and leave.partial:
        perm_s, perm_e = datetime.combine(work_date, leave.start), datetime.combine(work_date, leave.end)
        res.justified = leave.justified

    if first:
        ref_start = exp_start
        if shift.flexible and shift.latest_in:
            ref_start = datetime.combine(work_date, shift.latest_in)
        delay = _mins(first - ref_start)
        if delay > shift.late_grace and not (perm_e and first <= perm_e and perm_s <= ref_start + timedelta(minutes=shift.late_grace)):
            res.late_min = delay if not shift.flexible else delay
        if shift.earliest_in and first < datetime.combine(work_date, shift.earliest_in):
            res.anomalies.append("before_earliest_in")

    if complete and first and last:
        if n >= 4:
            res.worked_min = sum(_mins(pts[i + 1] - pts[i]) for i in range(0, n, 2))
        else:
            res.worked_min = max(0, res.presence_min - shift.break_min)
        target_end = first + timedelta(minutes=shift.expected_min + shift.break_min) if shift.flexible else exp_end
        short = _mins(target_end - last)
        if short > shift.early_grace and not (perm_s and perm_e and last >= perm_s and perm_e >= target_end):
            res.early_leave_min = short
        extra = res.worked_min - shift.expected_min if shift.flexible else _mins(last - exp_end)
        if extra >= shift.overtime_threshold:
            res.overtime_min = extra
        res.missing_min = max(0, shift.expected_min - res.worked_min)
        if res.presence_min > LONG_PRESENCE_MIN:
            res.anomalies.append("long_presence")
    return res
