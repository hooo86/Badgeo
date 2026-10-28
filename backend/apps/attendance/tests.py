from datetime import date, datetime, time, timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.employees.models import Employee
from apps.leaves.models import Leave
from apps.orgs.models import OrgUnit
from apps.schedules.models import Holiday, Rotation, Shift, ShiftAssignment

from . import engine
from .engine import LeaveSpec, ShiftSpec, compute_day
from .models import AttendanceDay, PunchEvent
from .services import recompute_day

D = date(2026, 3, 2)  # Monday
DAY = ShiftSpec(start=time(8), end=time(17), break_min=60, late_grace=5, expected_min=480)
NIGHT = ShiftSpec(start=time(22), end=time(6), break_min=30, expected_min=450, work_days=(0, 1, 2, 3, 4, 5, 6))
dt = lambda h, m=0, day=D: datetime.combine(day, time(h, m))
LATER = datetime(2026, 3, 10, 12)  # "now" well after the day


class EngineTests(SimpleTestCase):
    def test_on_time_within_grace(self):
        r = compute_day(D, [dt(8, 4), dt(17, 0)], DAY, now=LATER)
        self.assertEqual((r.status, r.late_min, r.early_leave_min, r.worked_min), ("present", 0, 0, 476))

    def test_late_counts_from_scheduled_start(self):
        r = compute_day(D, [dt(8, 20), dt(17, 0)], DAY, now=LATER)
        self.assertEqual(r.late_min, 20)

    def test_early_leave_and_overtime(self):
        self.assertEqual(compute_day(D, [dt(8), dt(16, 15)], DAY, now=LATER).early_leave_min, 45)
        r = compute_day(D, [dt(8), dt(18, 10)], DAY, now=LATER)
        self.assertEqual((r.overtime_min, r.early_leave_min), (70, 0))
        self.assertEqual(compute_day(D, [dt(8), dt(17, 20)], DAY, now=LATER).overtime_min, 0)  # below threshold

    def test_four_punches_exclude_actual_break(self):
        r = compute_day(D, [dt(8), dt(12, 15), dt(13, 0), dt(17)], DAY, now=LATER)
        self.assertEqual((r.presence_min, r.worked_min), (540, 495))

    def test_duplicate_punches_ignored(self):
        r = compute_day(D, [dt(8, 0), dt(8, 1), dt(17)], DAY, now=LATER)
        self.assertEqual(len(r.punches), 2)
        self.assertIn(engine.DUP, r.anomalies)

    def test_missing_exit_and_missing_entry(self):
        r = compute_day(D, [dt(8)], DAY, now=LATER)
        self.assertEqual((r.status, r.anomalies), ("incomplete", [engine.MISSING_OUT]))
        r = compute_day(D, [dt(17)], DAY, now=LATER)
        self.assertEqual((r.status, r.first_in, r.anomalies), ("incomplete", None, [engine.MISSING_IN]))

    def test_open_day_is_in_progress_not_incomplete(self):
        r = compute_day(D, [dt(8)], DAY, now=dt(11))
        self.assertEqual(r.status, "in_progress")

    def test_no_punch_is_not_absence_unless_configured(self):
        self.assertEqual(compute_day(D, [], DAY, now=LATER).status, "no_punch")
        self.assertEqual(compute_day(D, [], DAY, now=LATER, no_punch_is_absent=True).status, "absent")

    def test_leave_holiday_and_rest(self):
        self.assertEqual(compute_day(D, [], DAY, leave=LeaveSpec("sick", True), now=LATER).status, "sick")
        r = compute_day(D, [], DAY, leave=LeaveSpec("leave", False), now=LATER)
        self.assertEqual((r.status, r.justified), ("leave", False))
        self.assertEqual(compute_day(D, [], DAY, holiday=True, now=LATER).status, "holiday")
        self.assertEqual(compute_day(date(2026, 3, 7), [], DAY, now=LATER).status, "rest")  # Saturday
        r = compute_day(date(2026, 3, 7), [dt(9, 0, date(2026, 3, 7)), dt(12, 0, date(2026, 3, 7))], DAY, now=LATER)
        self.assertIn("punch_on_rest_day", r.anomalies)

    def test_partial_permission_covers_late_arrival(self):
        perm = LeaveSpec("permission", True, time(8), time(10))
        self.assertEqual(compute_day(D, [dt(9, 45), dt(17)], DAY, leave=perm, now=LATER).late_min, 0)
        self.assertEqual(compute_day(D, [dt(10, 30), dt(17)], DAY, leave=perm, now=LATER).late_min, 150)

    def test_night_shift_across_midnight(self):
        r = compute_day(D, [dt(21, 55), dt(6, 5, D + timedelta(days=1))], NIGHT, now=LATER)
        self.assertEqual((r.status, r.late_min, r.early_leave_min, r.presence_min), ("present", 0, 0, 490))
        r = compute_day(D, [dt(22, 40), dt(5, 30, D + timedelta(days=1))], NIGHT, now=LATER)
        self.assertEqual((r.late_min, r.early_leave_min), (40, 30))

    def test_flexible_shift(self):
        flex = ShiftSpec(start=time(7), end=time(19), latest_in=time(9, 30), expected_min=480, break_min=60,
                         flexible=True, late_grace=0)
        r = compute_day(D, [dt(9, 0), dt(18, 0)], flex, now=LATER)
        self.assertEqual((r.late_min, r.early_leave_min, r.overtime_min), (0, 0, 0))
        r = compute_day(D, [dt(10, 0), dt(18, 0)], flex, now=LATER)
        self.assertEqual((r.late_min, r.early_leave_min), (30, 60))


class PersistenceTests(TestCase):
    def setUp(self):
        self.emp = Employee.objects.create(matricule="E1", first_name="A", last_name="B")
        self.day = Shift.objects.create(name="Jour", start_time=time(8), end_time=time(17), work_days=[0, 1, 2, 3, 4])
        self.night = Shift.objects.create(name="Nuit", kind="night", start_time=time(22), end_time=time(6),
                                          break_minutes=30, work_days=[0, 1, 2, 3, 4, 5, 6])

    def punch(self, y, mo, d, h, mi=0):
        PunchEvent.objects.create(employee=self.emp, source="manual",
                                  timestamp=timezone.make_aware(datetime(y, mo, d, h, mi)))

    def test_overnight_punches_grouped_on_work_date(self):
        ShiftAssignment.objects.create(employee=self.emp, shift=self.night, valid_from=date(2026, 1, 1))
        self.punch(2026, 3, 2, 22, 0)
        self.punch(2026, 3, 3, 6, 0)
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 2)).status, "present")
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 3)).status, "no_punch")
        self.assertEqual(AttendanceDay.objects.get(work_date=date(2026, 3, 2)).punch_count, 2)

    def test_shift_change_applies_from_valid_from(self):
        ShiftAssignment.objects.create(employee=self.emp, shift=self.day, valid_from=date(2026, 1, 1), valid_to=date(2026, 3, 8))
        ShiftAssignment.objects.create(employee=self.emp, shift=self.night, valid_from=date(2026, 3, 9))
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 6)).shift, self.day)
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 10)).shift, self.night)

    def test_employee_assignment_beats_org_unit_and_nearest_unit_wins(self):
        parent = OrgUnit.objects.create(kind="direction", name="D")
        child = OrgUnit.objects.create(kind="service", name="S", parent=parent)
        self.emp.org_unit = child
        self.emp.save()
        ShiftAssignment.objects.create(org_unit=parent, shift=self.night, valid_from=date(2026, 1, 1))
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 2)).shift, self.night)
        ShiftAssignment.objects.create(org_unit=child, shift=self.day, valid_from=date(2026, 1, 1))
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 2)).shift, self.day)
        ShiftAssignment.objects.create(employee=self.emp, shift=self.night, valid_from=date(2026, 1, 1))
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 2)).shift, self.night)

    def test_holiday_and_leave(self):
        ShiftAssignment.objects.create(employee=self.emp, shift=self.day, valid_from=date(2026, 1, 1))
        Holiday.objects.create(date=date(2026, 3, 2), name="Férié")
        Holiday.objects.create(date=date(2020, 3, 3), name="Annuel", recurring=True)
        Leave.objects.create(employee=self.emp, kind="leave", start_date=date(2026, 3, 4), end_date=date(2026, 3, 5))
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 2)).status, "holiday")
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 3)).status, "holiday")
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 5)).status, "leave")
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 6)).status, "no_punch")

    def test_rotation(self):
        rot = Rotation.objects.create(name="R", anchor_date=date(2026, 3, 2), cycle=[self.day.id, self.night.id, None])
        ShiftAssignment.objects.create(employee=self.emp, rotation=rot, valid_from=date(2026, 1, 1))
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 2)).shift, self.day)
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 3)).shift, self.night)
        self.assertIsNone(recompute_day(self.emp, date(2026, 3, 4)).shift)
        self.assertEqual(recompute_day(self.emp, date(2026, 3, 5)).shift, self.day)

    def test_recompute_is_idempotent_and_keeps_raw_punches(self):
        ShiftAssignment.objects.create(employee=self.emp, shift=self.day, valid_from=date(2026, 1, 1))
        self.punch(2026, 3, 2, 8, 30)
        self.punch(2026, 3, 2, 17, 0)
        a = recompute_day(self.emp, date(2026, 3, 2))
        b = recompute_day(self.emp, date(2026, 3, 2))
        self.assertEqual((a.pk, b.late_min, PunchEvent.objects.count(), AttendanceDay.objects.count()), (a.pk, 30, 2, 1))
