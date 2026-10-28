from datetime import date

from apps.orgs.models import OrgUnit

from .models import Holiday, Shift, ShiftAssignment


def _unit_chain(unit):
    """The unit and its ancestors, nearest first."""
    chain = []
    while unit is not None:
        chain.append(unit.pk)
        unit = unit.parent
    return chain


def shift_for(employee, d: date):
    """Applicable Shift or None. Precedence: employee assignment > nearest org unit > ancestors;
    among equals the most recent valid_from wins. A rotation resolves to its shift (or None = rest day)."""
    qs = ShiftAssignment.objects.filter(valid_from__lte=d).exclude(valid_to__lt=d).select_related("shift", "rotation")
    own = qs.filter(employee=employee).first()
    chosen = own
    if chosen is None and employee.org_unit_id:
        chain = _unit_chain(employee.org_unit)
        unit_rows = {a.org_unit_id: a for a in reversed(list(qs.filter(org_unit_id__in=chain)))}
        for uid in chain:  # nearest first
            if uid in unit_rows:
                chosen = unit_rows[uid]
                break
    if chosen is None:
        return None
    if chosen.rotation_id:
        sid = chosen.rotation.shift_id_on(d)
        return Shift.objects.get(pk=sid) if sid else None
    return chosen.shift


def is_holiday(d: date) -> bool:
    return Holiday.objects.filter(date=d).exists() or Holiday.objects.filter(
        recurring=True, date__month=d.month, date__day=d.day).exists()
