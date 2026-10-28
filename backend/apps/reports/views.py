from datetime import date, timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasStaffRole
from rest_framework.response import Response

from apps.accounts.models import GLOBAL_ROLES, get_role
from apps.attendance.models import AttendanceDay, PunchEvent
from apps.attendance.services import local_naive
from apps.audit.utils import audit
from apps.corrections.models import Correction
from apps.devices.models import Device
from apps.orgs.models import OrgUnit

from .dashboard import scoped_employees
from .exporters import EXPORTERS, respond

STATUS_FR = {"present": "Présent", "in_progress": "En cours", "incomplete": "Incomplet", "no_punch": "Sans pointage",
             "absent": "Absent", "leave": "Congé", "sick": "Arrêt maladie", "mission": "Mission",
             "permission": "Permission", "holiday": "Férié", "rest": "Repos", "pending": "À venir", "scheduled": "Planifié"}
ANOM_FR = {"missing_out": "Sortie manquante", "missing_in": "Entrée manquante", "odd_punches": "Nombre impair",
           "duplicate_punch": "Doublon", "no_shift": "Sans horaire", "punch_on_rest_day": "Pointage jour de repos",
           "punch_on_holiday": "Pointage jour férié", "punch_during_leave": "Pointage pendant congé",
           "long_presence": "Présence > 16 h", "before_earliest_in": "Avant heure min. d'arrivée"}
hm = lambda m: "" if m is None else f"{m // 60}h{m % 60:02d}"
t = lambda dt: local_naive(dt).strftime("%H:%M") if dt else ""
name = lambda e: f"{e.last_name} {e.first_name}"


def _period(q):
    try:
        end = date.fromisoformat(q["to"]) if q.get("to") else timezone.localdate()
        start = date.fromisoformat(q["from"]) if q.get("from") else end.replace(day=1)
    except ValueError:
        raise ValueError("Dates attendues au format AAAA-MM-JJ.")
    if start > end or (end - start).days > 366:
        raise ValueError("Période invalide (maximum 366 jours).")
    return start, end


def _days(request, q, start, end):
    qs = AttendanceDay.objects.filter(employee__in=scoped_employees(request.user).values("id"), work_date__range=(start, end)
                                      ).select_related("employee", "employee__org_unit", "shift")
    if q.get("employee"):
        qs = qs.filter(employee_id=q["employee"])
    if q.get("matricule"):
        qs = qs.filter(employee__matricule__icontains=q["matricule"])
    if q.get("org_unit"):
        qs = qs.filter(employee__org_unit__in=OrgUnit.with_descendants([int(q["org_unit"])]))
    if q.get("device"):
        qs = qs.filter(employee__punches__device_id=q["device"], employee__punches__timestamp__date__range=(start, end)).distinct()
    if q.get("anomaly"):
        qs = qs.filter(anomalies__icontains=q["anomaly"])
    return qs.order_by("work_date", "employee__last_name")


def _unit(e):
    return e.org_unit.name if e.org_unit else ""


def r_daily(request, q, s, e):
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), _unit(d.employee),
             d.shift.name if d.shift else "", STATUS_FR.get(d.status, d.status), t(d.first_in), t(d.last_out),
             d.late_min or "", d.early_leave_min or "", hm(d.worked_min), hm(d.overtime_min) if d.overtime_min else "",
             ", ".join(ANOM_FR.get(a, a) for a in d.anomalies)] for d in _days(request, q, s, e)]
    return "État journalier des présences", ["Date", "Matricule", "Nom", "Unité", "Horaire", "Statut", "Entrée", "Sortie",
            "Retard (min)", "Départ anticipé (min)", "Travail estimé", "HS potentielles", "Anomalies"], rows


def r_monthly(request, q, s, e):
    agg = {}
    for d in _days(request, q, s, e):
        a = agg.setdefault(d.employee_id, {"emp": d.employee, "present": 0, "late_n": 0, "late": 0, "early": 0, "worked": 0,
                                           "ot": 0, "abs": 0, "abs_j": 0, "noP": 0, "inc": 0})
        a["present"] += d.status in ("present", "in_progress", "incomplete")
        a["late_n"] += d.late_min > 0
        a["late"] += d.late_min
        a["early"] += d.early_leave_min
        a["worked"] += d.worked_min or 0
        a["ot"] += d.overtime_min
        a["abs"] += d.status == "absent" or (d.status in ("leave", "sick", "mission", "permission") and d.justified is False)
        a["abs_j"] += d.status in ("leave", "sick", "mission", "permission") and d.justified is not False
        a["noP"] += d.status == "no_punch"
        a["inc"] += d.status == "incomplete"
    rows = [[a["emp"].matricule, name(a["emp"]), _unit(a["emp"]), a["present"], a["late_n"], a["late"], a["early"],
             hm(a["worked"]), hm(a["ot"]), a["abs"], a["abs_j"], a["noP"], a["inc"]] for a in agg.values()]
    return "État mensuel des présences", ["Matricule", "Nom", "Unité", "Jours présents", "Nb retards", "Retard cumulé (min)",
            "Départs anticipés (min)", "Heures travaillées", "HS potentielles", "Absences injustifiées",
            "Absences justifiées", "Sans pointage", "Incomplets"], sorted(rows, key=lambda r: r[1])


def r_late(request, q, s, e):
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), _unit(d.employee),
             t(d.first_in), d.late_min] for d in _days(request, q, s, e).filter(late_min__gt=0)]
    return "Retards", ["Date", "Matricule", "Nom", "Unité", "Arrivée", "Retard (min)"], rows


def r_absences(request, q, s, e):
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), _unit(d.employee),
             STATUS_FR.get(d.status, d.status), "Oui" if d.justified else ("Non" if d.justified is False else "—")]
            for d in _days(request, q, s, e).filter(status__in=("absent", "no_punch", "leave", "sick", "mission", "permission"))]
    return "Absences et absences justifiées", ["Date", "Matricule", "Nom", "Unité", "Nature", "Justifiée"], rows


def r_early(request, q, s, e):
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), _unit(d.employee), t(d.last_out),
             d.early_leave_min] for d in _days(request, q, s, e).filter(early_leave_min__gt=0)]
    return "Départs anticipés", ["Date", "Matricule", "Nom", "Unité", "Sortie", "Anticipation (min)"], rows


def r_hours(request, q, s, e):
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), hm(d.presence_min), hm(d.worked_min),
             hm(d.missing_min) if d.missing_min else ""] for d in _days(request, q, s, e).exclude(presence_min=None)]
    return "Heures de présence", ["Date", "Matricule", "Nom", "Présence", "Travail estimé", "Manquant"], rows


def r_overtime(request, q, s, e):
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), _unit(d.employee), hm(d.overtime_min)]
            for d in _days(request, q, s, e).filter(overtime_min__gt=0)]
    return "Heures supplémentaires potentielles (à valider)", ["Date", "Matricule", "Nom", "Unité", "HS potentielles"], rows


def r_anomalies(request, q, s, e):
    qs = _days(request, q, s, e).filter(status__in=("incomplete", "no_punch")) | _days(request, q, s, e).exclude(anomalies=[])
    rows = [[d.work_date.strftime("%d/%m/%Y"), d.employee.matricule, name(d.employee), _unit(d.employee),
             STATUS_FR.get(d.status, d.status), ", ".join(ANOM_FR.get(a, a) for a in d.anomalies) or "—",
             ", ".join(d.punch_times)] for d in qs.distinct().order_by("work_date", "employee__last_name")]
    return "Anomalies à traiter", ["Date", "Matricule", "Nom", "Unité", "Statut", "Anomalies", "Pointages"], rows


def r_raw(request, q, s, e):
    emps = scoped_employees(request.user).values("id")
    qs = PunchEvent.objects.filter(timestamp__date__range=(s, e)).select_related("device", "employee")
    if get_role(request.user) in GLOBAL_ROLES:
        pass
    else:
        qs = qs.filter(employee__in=emps)
    if q.get("device"):
        qs = qs.filter(device_id=q["device"])
    if q.get("employee"):
        qs = qs.filter(employee_id=q["employee"])
    rows = [[local_naive(p.timestamp).strftime("%d/%m/%Y %H:%M:%S"), p.device.name if p.device else p.get_source_display(),
             p.device_user_id, p.employee.matricule if p.employee else "(non rattaché)",
             name(p.employee) if p.employee else "", p.punch_type, p.verify_mode] for p in qs.order_by("timestamp")[:50000]]
    return "Pointages bruts par appareil", ["Date/heure", "Source", "ID appareil", "Matricule", "Nom", "Type", "Mode"], rows


def r_corrections(request, q, s, e):
    qs = Correction.objects.filter(employee__in=scoped_employees(request.user).values("id"), work_date__range=(s, e)
                                   ).select_related("employee", "created_by", "reviewed_by")
    rows = [[c.created_at.astimezone().strftime("%d/%m/%Y %H:%M"), c.work_date.strftime("%d/%m/%Y"), name(c.employee),
             c.get_kind_display(), c.new_timestamp.astimezone().strftime("%H:%M") if c.new_timestamp else c.new_status,
             c.reason, c.created_by.username, c.get_state_display(), c.reviewed_by.username if c.reviewed_by else "",
             c.review_note] for c in qs]
    return "Historique des corrections", ["Créée le", "Jour", "Employé", "Type", "Valeur", "Motif", "Auteur", "État",
            "Validée par", "Note"], rows


def r_devices(request, q, s, e):
    rows = [[d.name, d.get_vendor_display(), d.model, f"{d.ip_address}:{d.port}", d.get_status_display(),
             d.last_seen_at.astimezone().strftime("%d/%m/%Y %H:%M") if d.last_seen_at else "",
             d.last_sync_at.astimezone().strftime("%d/%m/%Y %H:%M") if d.last_sync_at else "", d.events_total,
             d.consecutive_failures, d.last_error] for d in Device.objects.all()]
    return "État de fonctionnement des pointeuses", ["Nom", "Fabricant", "Modèle", "Adresse", "État", "Dernier contact",
            "Dernière synchro", "Événements", "Échecs consécutifs", "Dernière erreur"], rows


REPORTS = {"daily": r_daily, "monthly": r_monthly, "late": r_late, "absences": r_absences, "early-leave": r_early,
           "hours": r_hours, "overtime": r_overtime, "anomalies": r_anomalies, "raw-punches": r_raw,
           "corrections": r_corrections, "devices": r_devices}
DEVICE_ONLY = {"devices"}


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasStaffRole])
def report(request, name_):
    fn = REPORTS.get(name_)
    if fn is None:
        return Response({"detail": f"Rapport inconnu. Disponibles: {sorted(REPORTS)}"}, status=404)
    role = get_role(request.user)
    if name_ in DEVICE_ONLY and role not in GLOBAL_ROLES:
        return Response({"detail": "Accès refusé."}, status=403)
    if role == "employee" or role is None:
        return Response({"detail": "Accès refusé."}, status=403)
    try:
        s, e = _period(request.query_params)
    except ValueError as ex:
        return Response({"detail": str(ex)}, status=400)
    fmt = request.query_params.get("fmt", "json")
    if fmt != "json" and fmt not in EXPORTERS:
        return Response({"detail": "fmt: json, csv, xlsx ou pdf."}, status=400)
    title, headers, rows = fn(request, request.query_params, s, e)
    audit(request, "report", detail={"report": name_, "fmt": fmt, "from": str(s), "to": str(e), "rows": len(rows)})
    if fmt == "json":
        return Response({"title": title, "headers": headers, "rows": rows[:5000], "total": len(rows)})
    return respond(fmt, f"badgeo-{name_}", title, headers, rows, f"Période du {s:%d/%m/%Y} au {e:%d/%m/%Y} – {len(rows)} ligne(s)")
