from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceDay, PunchEvent
from apps.attendance.services import recompute_day

from .models import Correction

OVERRIDE_STATUSES = {"present", "leave", "sick", "mission", "permission", "rest", "holiday", "absent"}
SNAP = ("status", "first_in", "last_out", "late_min", "early_leave_min", "worked_min", "punch_times")


def snapshot(day: AttendanceDay):
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k in SNAP for v in [getattr(day, k)]}


@transaction.atomic
def validate(correction: Correction, reviewer, note=""):
    if correction.state != Correction.State.PENDING:
        raise ValueError("Correction déjà traitée.")
    if reviewer.pk == correction.created_by_id:
        raise PermissionError("L'auteur d'une correction ne peut pas la valider.")
    if correction.kind == Correction.Kind.ADD_PUNCH:
        correction.result_punch = PunchEvent.objects.create(
            source=PunchEvent.Source.MANUAL, employee=correction.employee, timestamp=correction.new_timestamp)
    else:
        day, _ = AttendanceDay.objects.get_or_create(employee=correction.employee, work_date=correction.work_date,
                                                      defaults={"computed_status": "no_punch", "status": "no_punch"})
        day.override_status = correction.new_status
        day.save(update_fields=["override_status"])
    day = recompute_day(correction.employee, correction.work_date)
    correction.after = snapshot(day)
    correction.state, correction.reviewed_by, correction.reviewed_at = Correction.State.VALIDATED, reviewer, timezone.now()
    correction.review_note = note
    correction.save()
    return correction


def reject(correction: Correction, reviewer, note):
    if correction.state != Correction.State.PENDING:
        raise ValueError("Correction déjà traitée.")
    if not note.strip():
        raise ValueError("Un motif de rejet est obligatoire.")
    correction.state, correction.reviewed_by, correction.reviewed_at, correction.review_note = \
        Correction.State.REJECTED, reviewer, timezone.now(), note
    correction.save()
    return correction
