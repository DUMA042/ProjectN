from owl.rules.engine import get_rule

DAYS_MAP = {1: "monday", 2: "tuesday", 3: "wednesday", 4: "thursday", 5: "friday", 6: "saturday", 7: "sunday"}

import re as _re
from datetime import date as _date

_TIME_RE = _re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(:([0-5]\d))?$")
_IDENT_RE = _re.compile(r"^[A-Za-z_][\w.]*$")


def _require_time(value: object, field: str) -> str:
    """HH:MM[:SS] only — a broken rule value must fail loudly, never reach SQL."""
    s = str(value).strip()
    if not _TIME_RE.match(s):
        raise ValueError(f"Invalid time for '{field}': {value!r} (expected HH:MM)")
    return s


def _require_date(value: object, field: str) -> str:
    try:
        return _date.fromisoformat(str(value).strip()).isoformat()
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Invalid date for '{field}': {value!r} (expected YYYY-MM-DD)")


def _require_ident(value: object, field: str) -> str:
    s = str(value)
    if not _IDENT_RE.match(s):
        raise ValueError(f"Invalid identifier for '{field}': {value!r}")
    return s


def _quote_literal(value: object, field: str) -> str:
    s = str(value)
    if "'" in s:
        raise ValueError(f"Invalid value for '{field}': quotes are not allowed")
    return f"'{s}'"

def build_checkin_classification(column: str = "check_in_time", date_col: str = "swipe_date") -> str:
    column = _require_ident(column, "column")
    date_col = _require_ident(date_col, "date_col")
    wh = get_rule("working_hours", {})
    cases = []
    for dow, day_name in sorted(DAYS_MAP.items()):
        day_rules = wh.get(day_name)
        if day_rules is None:
            continue
        ci = day_rules.get("checkin", {})
        if not ci:
            continue
        eb = _require_time(ci.get("early_before", "08:30"), "early_before")
        ns = _require_time(ci.get("normal_start", "08:30"), "normal_start")
        ne = _require_time(ci.get("normal_end", "09:00"), "normal_end")
        la = _require_time(ci.get("late_after", "09:00"), "late_after")
        cases.append(
            f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow} AND {column} < TIME '{eb}' THEN 'Early Arrival'"
        )
        cases.append(
            f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow} AND {column} >= TIME '{ns}' AND {column} < TIME '{ne}' THEN 'Normal Arrival'"
        )
        cases.append(
            f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow} AND {column} >= TIME '{la}' THEN 'Late Arrival'"
        )
    if not cases:
        return "'Unclassified'"
    return f"CASE {' '.join(cases)} ELSE 'Unclassified' END"


def build_checkout_classification(column: str = "check_out_time", date_col: str = "swipe_date", incomplete_condition: str = "TRUE") -> str:
    column = _require_ident(column, "column")
    date_col = _require_ident(date_col, "date_col")
    wh = get_rule("working_hours", {})
    it = get_rule("incomplete_threshold", {"hours": 1})
    threshold_hours = it.get("hours", 1)
    cases = []
    for dow, day_name in sorted(DAYS_MAP.items()):
        day_rules = wh.get(day_name)
        if day_rules is None:
            continue
        co = day_rules.get("checkout", {})
        if not co:
            continue
        eb = _require_time(co.get("early_before", "17:00"), "early_before")
        ns = _require_time(co.get("normal_start", "17:00"), "normal_start")
        ne = _require_time(co.get("normal_end", "18:00"), "normal_end")
        la = _require_time(co.get("late_after", "18:00"), "late_after")
        prefix = f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow}"
        cases.append(
            f"{prefix} AND ({incomplete_condition}) THEN 'Incomplete'"
        )
        cases.append(
            f"{prefix} AND {column} < TIME '{eb}' THEN 'Early Departure'"
        )
        cases.append(
            f"{prefix} AND {column} >= TIME '{ns}' AND {column} < TIME '{ne}' THEN 'Normal Departure'"
        )
        cases.append(
            f"{prefix} AND {column} >= TIME '{la}' THEN 'Late Departure'"
        )
    if not cases:
        return "'Unclassified'"
    return f"CASE {' '.join(cases)} ELSE 'Unclassified' END"


def build_holidays_filter(date_col: str = "swipe_date") -> str:
    date_col = _require_ident(date_col, "date_col")
    h = get_rule("holidays", {})
    dates = h.get("dates", [])
    if not dates:
        return ""
    date_list = ", ".join(f"'{_require_date(d, 'holidays.dates')}'" for d in dates)
    return f"AND {date_col} NOT IN ({date_list})"


def get_working_weekdays() -> list:
    """ISO weekday numbers (1=Mon … 7=Sun) configured as working days.

    A weekday is a working day when its ``working_hours`` entry is not ``null``.
    Falls back to Mon–Fri if nothing is configured.
    """
    wh = get_rule("working_hours", {})
    dows = [dow for dow, day_name in sorted(DAYS_MAP.items()) if wh.get(day_name) is not None]
    return dows or [1, 2, 3, 4, 5]


def build_working_days_filter(date_col: str = "swipe_date") -> str:
    date_col = _require_ident(date_col, "date_col")
    dows = get_working_weekdays()
    return f"AND EXTRACT(ISODOW FROM {date_col}) IN ({','.join(str(d) for d in dows)})"


def get_eligible_statuses() -> list:
    es = get_rule("eligible_statuses", {})
    return es.get("statuses", ["Active"])


def get_active_statuses() -> list:
    """Configured eligible statuses; falls back to ['Active'] when empty."""
    raw = get_eligible_statuses() or []
    cleaned = [str(s).strip() for s in raw if s is not None and str(s).strip()]
    return cleaned or ["Active"]


def build_status_filter(alias: str = "s") -> str:
    """Case-insensitive IN clause against an employee_statuses alias."""
    alias = _require_ident(alias, "alias")
    names = get_active_statuses()
    quoted = ", ".join(_quote_literal(n.lower(), "statuses") for n in names)
    return f"LOWER({alias}.status_name) IN ({quoted})"


def build_eligible_statuses_filter() -> str:
    statuses = get_eligible_statuses()
    if not statuses:
        return "AND 1=1"
    quoted = ", ".join(_quote_literal(s, "statuses") for s in statuses)
    return f"AND LOWER(s.status_name) IN ({quoted.lower()})"
