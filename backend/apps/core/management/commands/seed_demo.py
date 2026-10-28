"""Simulation mode: fills the database with *synthetic* data to try screens and calculations without a terminal.
Simulated punches belong to a disabled device named "[SIMULATION] ..." so they are never confused with real ones
and are never synchronised. `--clear` removes everything this command created."""
import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import Profile
from apps.attendance.models import PunchEvent
from apps.attendance.services import recompute_range
from apps.devices.models import Device
from apps.employees.models import DeviceUserMap, Employee
from apps.leaves.models import Leave
from apps.orgs.models import OrgUnit
from apps.schedules.models import Holiday, Shift, ShiftAssignment

SIM = "[SIMULATION] Pointeuse virtuelle"
PREFIX = "SIM-"
PEOPLE = [("Garnier", "Sophie", "Fabrication"), ("Leroy", "Maxime", "Ingénierie"), ("Dubois", "Thomas", "Fabrication"),
          ("Ndong", "David", "Support"), ("Vasseur", "Amélie", "Commercial"), ("Benali", "Karim", "Logistique"),
          ("Moreau", "Léa", "Commercial"), ("Renard", "Camille", "Ingénierie"), ("Bensaid", "Karim", "Commercial"),
          ("Lemoine", "Marc", "Support"), ("Petit", "Julie", "Fabrication"), ("Roux", "Nadia", "Logistique")]


class Command(BaseCommand):
    help = "Create (or --clear) synthetic demo data."

    def add_arguments(self, p):
        p.add_argument("--clear", action="store_true")
        p.add_argument("--days", type=int, default=14)
        p.add_argument("--password", default="Demo-Badgeo-2026!")

    def handle(self, *a, clear=False, days=14, password="", **kw):
        PunchEvent.objects.filter(device__name=SIM).delete()
        Employee.objects.filter(matricule__startswith=PREFIX).delete()
        Device.objects.filter(name=SIM).delete()
        User.objects.filter(username__in=["demo_admin", "demo_rh", "demo_sophie"]).delete()
        if clear:
            return self.stdout.write("Données de simulation supprimées.")
        rng = random.Random(7)
        today = timezone.localdate()
        dev = Device.objects.create(name=SIM, vendor="zkteco", ip_address="192.0.2.1", port=4370, enabled=False,
                                    sync_interval_minutes=0, model="Simulation")
        units = {n: OrgUnit.objects.get_or_create(parent=None, name=n, defaults={"kind": "direction"})[0]
                 for n in ("Production", "Ingénierie & Support", "Commercial & Logistique")}
        group = {"Fabrication": "Production", "Ingénierie": "Ingénierie & Support", "Support": "Ingénierie & Support",
                 "Commercial": "Commercial & Logistique", "Logistique": "Commercial & Logistique"}
        day, _ = Shift.objects.get_or_create(name="Journée 8h-17h", defaults=dict(start_time=time(8), end_time=time(17), work_days=[0, 1, 2, 3, 4]))
        night, _ = Shift.objects.get_or_create(name="Nuit 22h-06h", defaults=dict(kind="night", start_time=time(22), end_time=time(6), break_minutes=30, work_days=[0, 1, 2, 3, 4, 5, 6]))
        for u in units.values():
            ShiftAssignment.objects.get_or_create(org_unit=u, shift=day, valid_from=today - timedelta(days=400))
        emps = []
        for i, (ln, fn, svc) in enumerate(PEOPLE, 1):
            e = Employee.objects.create(matricule=f"{PREFIX}{i:03d}", last_name=ln, first_name=fn, job_title=svc,
                                        org_unit=units[group[svc]], hire_date=date(2022, 1, 1) + timedelta(days=40 * i))
            DeviceUserMap.objects.create(employee=e, device=dev, device_user_id=str(100 + i))
            emps.append(e)
        ShiftAssignment.objects.create(employee=emps[-1], shift=night, valid_from=today - timedelta(days=400))
        Leave.objects.create(employee=emps[3], kind="leave", start_date=today - timedelta(days=3), end_date=today - timedelta(days=2))
        Holiday.objects.get_or_create(date=today - timedelta(days=9), defaults={"name": "Jour férié (simulation)"})
        aware = lambda d, h, m: timezone.make_aware(datetime.combine(d, time(h, m)))
        rows, now = [], timezone.localtime()
        for e in emps:
            for k in range(days, -1, -1):
                d = today - timedelta(days=k)
                if d.weekday() > 4 and e is not emps[-1] or d == today - timedelta(days=9) and e is not emps[-1]:
                    continue
                if e.matricule.endswith("004") and k in (2, 3):
                    continue  # on leave
                if rng.random() < 0.04:
                    continue  # no punch
                if e is emps[-1]:  # night worker
                    ins, outs = aware(d, 21, 55 + 0), aware(d + timedelta(days=1), 6, rng.randint(0, 6))
                    seq = [ins, outs]
                else:
                    late = rng.choice([0, 0, 0, 0, 2, 12, 25])
                    seq = [aware(d, 8, 0) + timedelta(minutes=late - rng.randint(0, 6)), aware(d, 12, rng.randint(0, 20)),
                           aware(d, 13, rng.randint(0, 20)), aware(d, 17, 0) + timedelta(minutes=rng.choice([0, 3, 10, 40, -30]))]
                    if rng.random() < 0.05:
                        seq = seq[:1]  # forgotten exit
                for ts in seq:
                    if ts <= now:
                        rows.append(PunchEvent(device=dev, device_user_id=e.device_ids.first().device_user_id, employee=e, timestamp=ts))
        PunchEvent.objects.bulk_create(rows)
        recompute_range(emps, today - timedelta(days=days), today)
        for name, role, emp in (("demo_admin", "sysadmin", None), ("demo_rh", "hr_manager", None), ("demo_sophie", "employee", emps[0])):
            u = User.objects.create_user(name, password=password, is_superuser=name == "demo_admin", is_staff=name == "demo_admin")
            Profile.objects.create(user=u, role=role)
            if emp:
                emp.user = u
                emp.save()
        self.stdout.write(f"{len(emps)} employés simulés, {len(rows)} pointages simulés. Comptes: demo_admin / demo_rh / demo_sophie (mot de passe: {password})")
