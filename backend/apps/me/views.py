"""Self-service endpoints for the mobile app. Identity always comes from the authenticated user."""
import ipaddress
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.attendance.models import AttendanceDay, PunchEvent
from apps.attendance.serializers import AttendanceDaySerializer
from apps.attendance.services import recompute_day
from apps.audit.utils import audit
from apps.schedules.services import is_holiday, shift_for

MIN_GAP_SECONDS = 30


def _employee(request):
    return getattr(request.user, "employee", None)


def _no_employee():
    return Response({"detail": "Aucun employé lié à ce compte."}, status=403)


def _client_ip(request):
    if settings.TRUST_X_FORWARDED_FOR:  # rightmost entry = the one appended by our own reverse proxy
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def _ip_allowed(request):
    cidrs = settings.MOBILE_PUNCH_ALLOWED_CIDRS
    if not cidrs:
        return True
    try:
        ip = ipaddress.ip_address(_client_ip(request))
    except ValueError:
        return False
    return any(ip in ipaddress.ip_network(c, strict=False) for c in cidrs)


def _day_payload(emp, d):
    day = AttendanceDay.objects.filter(employee=emp, work_date=d).first() or recompute_day(emp, d)
    return AttendanceDaySerializer(day).data


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    emp = _employee(request)
    if not emp:
        return _no_employee()
    today = timezone.localdate()
    return Response({
        "employee": {"id": emp.pk, "matricule": emp.matricule, "first_name": emp.first_name, "last_name": emp.last_name,
                     "job_title": emp.job_title, "org_unit": emp.org_unit.name if emp.org_unit else None},
        "mobile_punch_enabled": settings.MOBILE_PUNCH_ENABLED,
        "mobile_punch_allowed_here": settings.MOBILE_PUNCH_ENABLED and _ip_allowed(request),
        "today": _day_payload(emp, today),
        "server_time": timezone.localtime().isoformat(timespec="seconds"),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def punch(request):
    emp = _employee(request)
    if not emp:
        return _no_employee()
    if not settings.MOBILE_PUNCH_ENABLED:
        return Response({"detail": "Le pointage mobile est désactivé par l'administrateur."}, status=403)
    if emp.status != "active":
        return Response({"detail": "Employé non actif."}, status=403)
    if not _ip_allowed(request):
        return Response({"detail": "Pointage mobile autorisé uniquement depuis le réseau de l'entreprise."}, status=403)
    now = timezone.now()  # server time only: the client clock is never trusted
    last = PunchEvent.objects.filter(employee=emp).order_by("-timestamp").first()
    if last and (now - last.timestamp).total_seconds() < MIN_GAP_SECONDS:
        return Response({"detail": "Pointage déjà enregistré à l'instant."}, status=429)
    ev = PunchEvent.objects.create(source=PunchEvent.Source.MOBILE, employee=emp, device_user_id=emp.matricule, timestamp=now)
    audit(request, "mobile_punch", ev)
    return Response({"timestamp": timezone.localtime(ev.timestamp).isoformat(timespec="seconds"),
                     "today": _day_payload(emp, timezone.localdate(ev.timestamp))}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def history(request):
    emp = _employee(request)
    if not emp:
        return _no_employee()
    try:
        start = date.fromisoformat(request.query_params["from"])
        end = date.fromisoformat(request.query_params["to"])
    except (KeyError, ValueError):
        return Response({"detail": "Paramètres from/to (AAAA-MM-JJ) requis."}, status=400)
    if (end - start).days > 92:
        return Response({"detail": "Période limitée à 92 jours."}, status=400)
    days = list(AttendanceDay.objects.filter(employee=emp, work_date__range=(start, end))
                .select_related("shift", "employee").order_by("-work_date"))
    ser = AttendanceDaySerializer(days, many=True).data
    return Response({"days": ser, "totals": {
        "worked_min": sum(d["worked_min"] or 0 for d in ser),
        "late_min": sum(d["late_min"] for d in ser),
        "overtime_min": sum(d["overtime_min"] for d in ser),
        "expected_min": sum(d.shift.expected_minutes for d in days
                            if d.shift and d.status not in ("holiday", "rest", "leave", "sick")),
    }})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def planning(request):
    emp = _employee(request)
    if not emp:
        return _no_employee()
    start = timezone.localdate()
    out = []
    for i in range(14):
        d = start + timedelta(days=i)
        s = shift_for(emp, d)
        works = bool(s and s.works_on(d))
        out.append({"date": d.isoformat(), "holiday": is_holiday(d),
                    "shift": {"name": s.name, "start": s.start_time.strftime("%H:%M"), "end": s.end_time.strftime("%H:%M"),
                              "crosses_midnight": s.crosses_midnight} if works else None})
    return Response({"days": out})
