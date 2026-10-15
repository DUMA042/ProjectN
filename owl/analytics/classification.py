"""Rule-driven attendance classification shared by the employee endpoints and the
analytics fact-table builder. Everything here reads Rule Settings — nothing is
hardcoded (working hours, holidays, eligible statuses, incomplete threshold,
leave-overrides-training).
"""
from __future__ import annotations

from datetime import date, timedelta

from owl.rules.engine import get_rule
from owl.rules.query_builder import get_active_statuses, get_working_weekdays

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def hm_to_min(t):
    try:
        h, m = str(t).split(":")[:2]
        return int(h) * 60 + int(m)
    except Exception:
        return None


def fmt_hours(minutes):
    if minutes is None:
        return None
    h = int(minutes // 60)
    m = int(round(minutes % 60))
    if h and m:
        return f"{h}h {m:02d}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def load_rule_context():
    """Snapshot of all rule-driven inputs needed for classification."""
    working_hours = get_rule("working_hours", {}) or {}
    incomplete_hours = (get_rule("incomplete_threshold", {"hours": 1}) or {}).get("hours", 1)
    working_dows = set(get_working_weekdays())
    leave_overrides_training = bool(get_rule("leave_overrides_training", True))
    active_statuses = {s.lower() for s in get_active_statuses()}
    holiday_raw = (get_rule("holidays", {}) or {}).get("dates", []) or []
    holiday_set = set()
    for d in holiday_raw:
        try:
            holiday_set.add(date.fromisoformat(str(d)))
        except ValueError:
            pass
    return {
        "working_hours": working_hours,
        "incomplete_hours": incomplete_hours,
        "working_dows": working_dows,
        "leave_overrides_training": leave_overrides_training,
        "active_statuses": active_statuses,
        "holiday_set": holiday_set,
        "holidays_raw": list(holiday_raw),
    }


def validate_rule_context(ctx=None) -> list[str]:
    """Audit rule values for garbage that would silently misclassify.

    Returns human-readable warnings (empty when clean). Pure — no I/O.
    Checks time thresholds parse, holiday dates parse, and the incomplete
    threshold is a positive number. Callers log these instead of letting
    bad rules degrade silently into None/'Unclassified'.
    """
    from owl.logger import get_logger

    ctx = ctx or load_rule_context()
    log = get_logger(__name__)
    warnings: list[str] = []
    wh = ctx.get("working_hours") or {}
    for day_name, day_rules in wh.items():
        if not isinstance(day_rules, dict):
            warnings.append(f"working_hours.{day_name} is not an object — day skipped")
            continue
        for section in ("checkin", "checkout"):
            part = day_rules.get(section) or {}
            if not isinstance(part, dict):
                continue
            for field, value in part.items():
                if hm_to_min(value) is None:
                    warnings.append(
                        f"working_hours.{day_name}.{section}.{field} "
                        f"is not a valid HH:MM time ({value!r})"
                    )
    for d in (ctx.get("holidays_raw") or []):
        try:
            date.fromisoformat(str(d))
        except ValueError:
            warnings.append(f"holidays entry is not a valid date ({d!r})")
    try:
        hours = float(ctx.get("incomplete_hours", 1))
        if hours <= 0:
            warnings.append(f"incomplete_threshold hours must be positive ({hours!r})")
    except (TypeError, ValueError):
        warnings.append("incomplete_threshold hours is not a number")
    for w in warnings:
        log.warning("rule context: %s", w)
    return warnings


def working_days_in_range(start: date, end: date, ctx=None):
    """Set of dates that are working days (configured weekdays minus holidays)."""
    ctx = ctx or load_rule_context()
    working_dows = ctx["working_dows"]
    holiday_set = ctx["holiday_set"]
    days = set()
    cur = start
    while cur <= end:
        if (cur.weekday() + 1) in working_dows and cur not in holiday_set:
            days.add(cur)
        cur += timedelta(days=1)
    return days


def classify_day(d, leave_ranges, training_ranges, swipe_dates, ctx, is_active, today):
    if (d.weekday() + 1) not in ctx["working_dows"]:
        return "weekend"
    if d in ctx["holiday_set"]:
        return "holiday"
    on_leave = any(ls <= d <= le for ls, le in leave_ranges)
    on_training = any(ts <= d <= te for ts, te in training_ranges)
    if on_leave and on_training:
        return "leave" if ctx["leave_overrides_training"] else "training"
    if on_leave:
        return "leave"
    if on_training:
        return "training"
    if d in swipe_dates:
        return "present"
    if not is_active:
        return "inactive"
    if d >= today:
        return "upcoming"
    return "absent"


def classify_checkin(t, wh):
    if not t or not wh or not wh.get("checkin"):
        return None
    ci = wh["checkin"]
    tm = hm_to_min(t)
    if tm is None:
        return None
    eb = hm_to_min(ci.get("early_before", "08:30"))
    ns = hm_to_min(ci.get("normal_start", "08:30"))
    ne = hm_to_min(ci.get("normal_end", "09:00"))
    la = hm_to_min(ci.get("late_after", "09:00"))
    if eb is not None and tm < eb:
        return "Early Arrival"
    if ns is not None and ne is not None and ns <= tm < ne:
        return "Normal Arrival"
    if la is not None and tm >= la:
        return "Late Arrival"
    return "Unclassified"


def classify_checkout(checkin_t, checkout_t, wh, incomplete_hours):
    if not checkout_t or not wh or not wh.get("checkout"):
        return None
    co = wh["checkout"]
    tm = hm_to_min(checkout_t)
    if tm is None:
        return None
    if checkin_t:
        cim = hm_to_min(checkin_t)
        if cim is not None and (tm - cim) < (incomplete_hours * 60):
            return "Incomplete"
    eb = hm_to_min(co.get("early_before", "17:00"))
    ns = hm_to_min(co.get("normal_start", "17:00"))
    ne = hm_to_min(co.get("normal_end", "18:00"))
    la = hm_to_min(co.get("late_after", "18:00"))
    if eb is not None and tm < eb:
        return "Early Departure"
    if ns is not None and ne is not None and ns <= tm < ne:
        return "Normal Departure"
    if la is not None and tm >= la:
        return "Late Departure"
    return "Unclassified"
