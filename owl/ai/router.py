"""Deterministic intent router — answers common questions with ZERO model calls.

The model is consulted only for questions nothing here recognizes. This makes
core intents reliable, instant, free, and fully private: no external request
happens at all on a router hit. Envelopes mirror the planner contract and
carry IR v2 (see ir2.py), so router output flows through the same validator,
policy, compiler, and executor as model output.
"""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

TOP_N_RE = re.compile(r"\btop\s+(\d{1,3})\b")
NUM_FIRST_RE = re.compile(r"\b(\d{1,3})\s+(earliest|latest|most)\b")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _norm(s: str) -> str:
    return " ".join(str(s).lower().split())


def _month_param(q: str, today: date) -> str | None:
    for name, num in MONTHS.items():
        if re.search(rf"\b{name}\b", q):
            year = today.year if num <= today.month else today.year - 1
            m = YEAR_RE.search(q)
            if m:
                year = int(m.group(0))
            return f"{year:04d}-{num:02d}"
    return None


def _month_bounds(month: str) -> tuple[str, str]:
    y, m = int(month[:4]), int(month[5:7])
    nm = m + 1 if m < 12 else 1
    ny = y if m < 12 else y + 1
    return f"{month}-01", f"{ny:04d}-{nm:02d}-01"


def _top_n(q: str, default: int = 5) -> int:
    m = TOP_N_RE.search(q) or NUM_FIRST_RE.search(q)
    if m:
        try:
            return max(1, min(50, int(m.group(1))))
        except ValueError:
            pass
    return default


def _names(session: Session, table: str, column: str) -> list[str]:
    rows = session.execute(text(f"SELECT {column} FROM {table}")).fetchall()
    return [str(r[0]) for r in rows if r[0]]


def _match_entity(q: str, values: list[str]) -> str | None:
    qn = f" {_norm(q)} "
    for v in sorted(values, key=len, reverse=True):
        vn = _norm(v)
        if vn and f" {vn} " in qn:
            return v
    return None


def _rule_answer(snapshot: dict, topic: str) -> str | None:
    rules = snapshot.get("rules", {}) or {}
    wh = rules.get("working_hours", {}) or {}
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def windows(kind: str, key: str) -> str:
        parts = []
        for d in days:
            w = (wh.get(d) or {}).get(kind, {}) or {}
            if w.get(key):
                parts.append(f"{d[:3].title()}: {w[key]}")
        return "; ".join(parts) if parts else "not configured"

    if topic == "late_checkout":
        return f"Late checkout starts at — {windows('checkout', 'late_after')}."
    if topic == "late_checkin":
        return f"Late check-in starts at — {windows('checkin', 'late_after')}."
    if topic == "early_checkin":
        return f"Early check-in is before — {windows('checkin', 'early_before')}."
    if topic == "early_checkout":
        return f"Early checkout is before — {windows('checkout', 'early_before')}."
    if topic == "incomplete":
        hrs = (rules.get("incomplete_threshold", {}) or {}).get("hours", 1)
        return f"A day counts as incomplete when the first-to-last swipe gap is under {hrs} hour(s)."
    if topic == "holidays":
        dates = (rules.get("holidays", {}) or {}).get("dates", []) or []
        if not dates:
            return "No holidays are currently configured."
        return f"Configured holidays ({len(dates)}): {', '.join(sorted(str(d) for d in dates))}."
    if topic == "working_days":
        on = [d[:3].title() for d in days if wh.get(d) is not None]
        return f"Working days: {', '.join(on) if on else 'Mon–Fri (default)'}."
    if topic == "eligible":
        sts = (rules.get("eligible_statuses", {}) or {}).get("statuses", ["Active"])
        return f"Attendance is taken for statuses: {', '.join(sts)}."
    return None


RULE_PATTERNS = [
    (("late", "check-out", "checkout", "check out", "departure"), "late_checkout"),
    (("late", "check-in", "checkin", "check in", "arrival", "arrive"), "late_checkin"),
    (("early", "check-in", "checkin", "arrival"), "early_checkin"),
    (("early", "check-out", "checkout", "departure", "leave early", "knock off"), "early_checkout"),
    (("incomplete", "single swipe", "one swipe"), "incomplete"),
    (("holiday", "public holiday", "day off"), "holidays"),
    (("working day", "workday", "work day", "which days"), "working_days"),
    (("eligible", "status", "who counts", "active"), "eligible"),
]


def _rule_topic(q: str) -> str | None:
    for keywords, topic in RULE_PATTERNS:
        if all(k in q for k in keywords[:1]) and any(k in q for k in keywords):
            # First keyword anchors the family; any keyword confirms it.
            return topic
    return None


def _dept_or_loc(session: Session, q: str) -> tuple[str | None, str | None]:
    dept = _match_entity(q, _names(session, "departments", "department_name"))
    loc = _match_entity(q, _names(session, "locations", "location_name"))
    return dept, loc


_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _period_label(month: str | None, day: str | None) -> str | None:
    if day:
        try:
            y, m, d = day.split("-")
            return f"{int(d)} {_MONTH_NAMES[int(m) - 1]} {y}"
        except (ValueError, IndexError):
            return day
    if month:
        try:
            y, m = month.split("-")
            return f"{_MONTH_NAMES[int(m) - 1]} {y}"
        except (ValueError, IndexError):
            return month
    return None


def _scope_filters(dept: str | None, loc: str | None) -> dict | None:
    kids = []
    if dept:
        kids.append({"field": "department", "operator": "=", "value": dept})
    if loc:
        kids.append({"field": "location", "operator": "=", "value": loc})
    if not kids:
        return None
    if len(kids) == 1:
        return kids[0]
    return {"and": kids}


def _absent_case() -> dict:
    return {
        "case": {
            "whens": [{"when": {"field": "status", "operator": "=", "value": "absent"}, "then": 1}],
            "else": 0,
        }
    }


def _present_case() -> dict:
    return {
        "case": {
            "whens": [{"when": {"field": "status", "operator": "=", "value": "present"}, "then": 1}],
            "else": 0,
        }
    }


def _month_window(entity: str, month: str) -> dict:
    lo, hi = _month_bounds(month)
    col = {"attendance": "work_date"}.get(entity, "work_date")
    return {"and": [
        {"field": col, "operator": ">=", "value": lo},
        {"field": col, "operator": "<", "value": hi},
    ]}


def _non_null(filt: dict | None, field: str) -> dict:
    """AND an IS NOT NULL guard so NULL times can't top a DESC ranking
    (Postgres sorts NULLS FIRST on DESC)."""
    guard: dict = {"field": field, "operator": "IS NOT NULL"}
    if filt is None:
        return guard
    return {"and": [filt, guard]}


def route(question: str, session: Session, snapshot: dict, today: date) -> dict | None:
    """Deterministic match -> envelope dict, or None (fall through to the model)."""
    q = _norm(question)
    month = _month_param(q, today)
    day = None
    if re.search(r"\byesterday\b", q):
        from datetime import timedelta

        day = (today - timedelta(days=1)).isoformat()
    elif re.search(r"\btoday\b", q):
        day = today.isoformat()

    dept, loc = _dept_or_loc(session, q)

    def scoped(base: dict | None) -> dict | None:
        scope = _scope_filters(dept, loc)
        if scope is None:
            return base
        if base is None:
            return scope
        return {"and": [base, scope]}

    has = lambda *ws: any(w in q for w in ws)  # noqa: E731

    # Rule questions first (no DB rows needed — direct answers).
    topic = _rule_topic(q)
    if topic and not has("who", "which staff", "top ", "list", "show me", "give me"):
        answer = _rule_answer(snapshot, topic)
        if answer:
            return {"type": "direct", "answer": answer}

    # On leave (default window: today — "who is on leave" means now).
    if has("on leave", "leave today", "leave list", "who is on leave", "who are on leave"):
        if day is not None:
            window: dict | None = {"and": [
                {"field": "start_date", "operator": "<=", "value": day},
                {"field": "end_date", "operator": ">=", "value": day},
            ]}
            period = _period_label(None, day)
        elif month is not None:
            lo, hi = _month_bounds(month)
            window = {"and": [
                {"field": "start_date", "operator": "<", "value": hi},
                {"field": "end_date", "operator": ">=", "value": lo},
            ]}
            period = _period_label(month, None)
        else:
            t = today.isoformat()
            window = {"and": [
                {"field": "start_date", "operator": "<=", "value": t},
                {"field": "end_date", "operator": ">=", "value": t},
            ]}
            period = _period_label(None, t)
        return {"type": "query", "template": "on_leave", "period": period, "ir": {
            "source": "leave",
            "select": [{"field": "full_name"}, {"field": "start_date"}, {"field": "end_date"}],
            "filters": scoped(window),
            "order_by": [{"field": "start_date", "direction": "ASC"}],
            "limit": 50,
        }}

    # Top early arrivals.
    if has("earl", "first to arrive", "first in", "early bird"):
        n = _top_n(q)
        filt = scoped(_month_window("attendance", month) if month else None)
        if day is not None:
            day_f: dict | None = {"field": "work_date", "operator": "=", "value": day}
            filt = {"and": [filt, day_f]} if filt else day_f
        filt = _non_null(filt, "checkin_time")
        return {"type": "query", "template": "top_early",
                "period": _period_label(month, day), "ir": {
            "source": "attendance",
            "select": [{"field": "full_name"}, {"field": "checkin_time"}],
            "filters": filt,
            "order_by": [{"field": "checkin_time", "direction": "ASC"}],
            "limit": n,
        }}

    # Absent most.
    if has("absent", "absence", "missing", "no show", "no-show"):
        n = _top_n(q)
        m = month or today.strftime("%Y-%m")
        filt = scoped(_month_window("attendance", m))
        return {"type": "query", "template": "top_absent",
                "period": _period_label(m, None), "ir": {
            "source": "attendance",
            "select": [{"field": "full_name"},
                       {"aggregate": "SUM", "expression": _absent_case(), "alias": "absent_days"}],
            "filters": filt,
            "group_by": ["full_name"],
            "order_by": [{"field": "absent_days", "direction": "DESC"}],
            "limit": n,
        }}

    # Late arrivals vs late checkouts — split on wording ("late checkout" must
    # never be answered with check-in times).
    if has("late", "latecomer", "tardy", "behind time"):
        n = _top_n(q)
        filt = scoped(_month_window("attendance", month) if month else None)
        if day is not None:
            day_f = {"field": "work_date", "operator": "=", "value": day}
            filt = {"and": [filt, day_f]} if filt else day_f
        if has("checkout", "check-out", "check out", "departure", "knock off", "closing"):
            filt = _non_null(filt, "checkout_time")
            return {"type": "query", "template": "late_checkouts",
                    "period": _period_label(month, day), "ir": {
                "source": "attendance",
                "select": [{"field": "full_name"}, {"field": "checkout_time"}],
                "filters": filt,
                "order_by": [{"field": "checkout_time", "direction": "DESC"}],
                "limit": n,
            }}
        filt = _non_null(filt, "checkin_time")
        return {"type": "query", "template": "late_comers",
                "period": _period_label(month, day), "ir": {
            "source": "attendance",
            "select": [{"field": "full_name"}, {"field": "checkin_time"}],
            "filters": filt,
            "order_by": [{"field": "checkin_time", "direction": "DESC"}],
            "limit": n,
        }}

    # Top-N working hours (minutes) per employee — checked BEFORE the general
    # rates branch: "top 5 ... most working hours" is a person ranking, not
    # a department aggregate.
    if has("most hours", "working hours", "overtime", "longest") and has("top", "most", "highest", "best"):
        n = _top_n(q)
        m = month or today.strftime("%Y-%m")
        filt = scoped(_month_window("attendance", m))
        return {"type": "query", "template": "top_hours",
                "period": _period_label(m, None), "ir": {
            "source": "attendance",
            "select": [{"field": "full_name"},
                       {"aggregate": "SUM", "field": "minutes_worked", "alias": "total_minutes"}],
            "filters": filt,
            "group_by": ["full_name"],
            "order_by": [{"field": "total_minutes", "direction": "DESC"}],
            "limit": n,
        }}

    # Department rates / working hours aggregates.
    if has("rate", "working hours", "hours worked", "utilization", "availability"):
        m = month or today.strftime("%Y-%m")
        filt = scoped(_month_window("attendance", m))
        return {"type": "query", "template": "dept_rate",
                "period": _period_label(m, None), "ir": {
            "source": "attendance",
            "select": [{"field": "department"},
                       {"aggregate": "SUM", "expression": _present_case(), "alias": "present_days"},
                       {"aggregate": "COUNT", "field": "*", "alias": "expected_days"},
                       {"aggregate": "SUM", "field": "minutes_worked", "alias": "total_minutes"}],
            "filters": filt,
            "group_by": ["department"],
            "limit": 100,
        }}

    return None
