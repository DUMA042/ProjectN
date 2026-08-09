from owl.rules.engine import get_rule

DAYS_MAP = {1: "monday", 2: "tuesday", 3: "wednesday", 4: "thursday", 5: "friday", 6: "saturday", 7: "sunday"}

def build_checkin_classification(column: str = "check_in_time", date_col: str = "swipe_date") -> str:
    wh = get_rule("working_hours", {})
    cases = []
    for dow, day_name in sorted(DAYS_MAP.items()):
        day_rules = wh.get(day_name)
        if day_rules is None:
            continue
        ci = day_rules.get("checkin", {})
        if not ci:
            continue
        cases.append(
            f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow} AND {column} < TIME '{ci.get('early_before', '08:30')}' THEN 'Early Arrival'"
        )
        cases.append(
            f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow} AND {column} >= TIME '{ci.get('normal_start', '08:30')}' AND {column} < TIME '{ci.get('normal_end', '09:00')}' THEN 'Normal Arrival'"
        )
        cases.append(
            f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow} AND {column} >= TIME '{ci.get('late_after', '09:00')}' THEN 'Late Arrival'"
        )
    if not cases:
        return "'Unclassified'"
    return f"CASE {' '.join(cases)} ELSE 'Unclassified' END"


def build_checkout_classification(column: str = "check_out_time", date_col: str = "swipe_date", incomplete_condition: str = "TRUE") -> str:
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
        prefix = f"WHEN EXTRACT(ISODOW FROM {date_col}) = {dow}"
        cases.append(
            f"{prefix} AND ({incomplete_condition}) THEN 'Incomplete'"
        )
        cases.append(
            f"{prefix} AND {column} < TIME '{co.get('early_before', '17:00')}' THEN 'Early Departure'"
        )
        cases.append(
            f"{prefix} AND {column} >= TIME '{co.get('normal_start', '17:00')}' AND {column} < TIME '{co.get('normal_end', '18:00')}' THEN 'Normal Departure'"
        )
        cases.append(
            f"{prefix} AND {column} >= TIME '{co.get('late_after', '18:00')}' THEN 'Late Departure'"
        )
    if not cases:
        return "'Unclassified'"
    return f"CASE {' '.join(cases)} ELSE 'Unclassified' END"


def build_holidays_filter(date_col: str = "swipe_date") -> str:
    h = get_rule("holidays", {})
    dates = h.get("dates", [])
    if not dates:
        return ""
    date_list = ", ".join(f"'{d}'" for d in dates)
    return f"AND {date_col} NOT IN ({date_list})"


def build_working_days_filter(date_col: str = "swipe_date") -> str:
    wh = get_rule("working_hours", {})
    active_dows = []
    for dow, day_name in sorted(DAYS_MAP.items()):
        if wh.get(day_name) is not None:
            active_dows.append(str(dow))
    if not active_dows:
        return "AND EXTRACT(ISODOW FROM swipe_date) BETWEEN 1 AND 5"
    return f"AND EXTRACT(ISODOW FROM {date_col}) IN ({','.join(active_dows)})"


def get_eligible_statuses() -> list:
    es = get_rule("eligible_statuses", {})
    return es.get("statuses", ["Active"])


def build_eligible_statuses_filter() -> str:
    statuses = get_eligible_statuses()
    if not statuses:
        return "AND 1=1"
    quoted = ", ".join(f"'{s}'" for s in statuses)
    return f"AND LOWER(s.status_name) IN ({quoted.lower()})"
