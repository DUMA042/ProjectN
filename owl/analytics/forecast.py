"""Forecast layer for the Forecast tab — honest statistical projections.

Method: least-squares linear trend over weekly aggregates of the trailing
window, with a ±1σ residual band. Coverage outlook combines that with *real*
future data (scheduled training rows). Everything is scoped like the rest of
the page (location + dimension filters).
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from sqlalchemy import text

from owl.analytics.filters import build_scope
from owl.load.database import get_session

METHOD_NOTE = (
    "Projection = linear trend over weekly history ± 1σ of residuals. "
    "Coverage outlook also subtracts scheduled training (known future data). "
    "Statistical guidance, not a guarantee."
)


def _linfit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs) or 1.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    a = my - b * mx
    return a, b


def _project(series: list[tuple[str, float]], horizon: int) -> dict:
    """Linear projection of a weekly series with ±1σ residual band."""
    ys = [v for _, v in series if v is not None]
    if len(ys) < 3:
        avg = sum(ys) / len(ys) if ys else None
        band = 0.0
        return {"fit": None, "avg": avg, "sigma": band}
    xs = list(range(len(series)))
    a, b = _linfit([float(x) for x in xs], [float(y) for y in ys])
    fitted = [a + b * x for x in xs]
    residuals = [y - f for y, f in zip(ys, fitted)]
    sigma = (sum(r * r for r in residuals) / len(residuals)) ** 0.5
    points = []
    for k in range(1, horizon + 1):
        x = len(series) - 1 + k
        v = a + b * x
        points.append((x, v, sigma))
    return {"fit": (a, b), "avg": sum(ys) / len(ys), "sigma": sigma, "points": points}


def _week_bounds(d: date) -> tuple[date, date]:
    """Monday..Sunday of the week containing d."""
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def build_forecast(
    filters: dict | None = None,
    window_weeks: int = 12,
    horizon_weeks: int = 8,
    outlook_weeks: int = 4,
) -> dict:
    today = date.today()
    hist_start = today - timedelta(weeks=window_weeks)

    with get_session() as s:
        params: dict = {"start": hist_start}
        joins, where = build_scope(filters, params)

        # ── Weekly attendance + leave aggregates ────────────────────────────
        weekly = s.execute(text(f"""
            SELECT date_trunc('week', ad.work_date)::date AS wk,
                   COUNT(*) FILTER (WHERE ad.is_working_day) AS wd,
                   COUNT(*) FILTER (WHERE ad.status = 'present') AS pd,
                   COUNT(DISTINCT ad.id_no) FILTER (WHERE ad.status = 'leave') AS on_leave
            FROM attendance_daily ad JOIN employees e ON e.id_no = ad.id_no
            {joins}
            {combine(where, 'ad.work_date >= :start')}
            GROUP BY 1 ORDER BY 1
        """), params).fetchall()

        att_series: list[tuple[str, float]] = []
        leave_series: list[tuple[str, float]] = []
        for wk, wd, pd, on_leave in weekly:
            if wd:
                att_series.append((wk.isoformat(), round(100.0 * pd / wd, 1)))
                leave_series.append((wk.isoformat(), float(on_leave or 0)))

        # ── Coverage outlook inputs ─────────────────────────────────────────
        active_rows = s.execute(text(f"""
            SELECT COALESCE(d.department_name, 'Unknown') AS dept, COUNT(*) AS n
            FROM employees e
            LEFT JOIN departments d ON d.department_id = e.department_id
            {joins}
            {combine(where, active_status_clause())}
            GROUP BY 1
        """), params).fetchall()

        leave_dept_rows = s.execute(text(f"""
            SELECT COALESCE(d.department_name, 'Unknown') AS dept,
                   date_trunc('week', ad.work_date)::date AS wk,
                   COUNT(DISTINCT ad.id_no) AS n
            FROM attendance_daily ad
            JOIN employees e ON e.id_no = ad.id_no
            LEFT JOIN departments d ON d.department_id = e.department_id
            {joins}
            {combine(where, 'ad.work_date >= :start AND ad.status = \'leave\'')}
            GROUP BY 1, 2
        """), params).fetchall()

        # ── Scheduled future training (per employee, for the outlook grid) ──
        horizon_end = today + timedelta(weeks=outlook_weeks)
        raw_train = s.execute(text(f"""
            SELECT COALESCE(d.department_name, 'Unknown') AS dept, tr.id_no, tr.start_date, tr.end_date
            FROM employee_trainings tr
            JOIN employees e ON e.id_no = tr.id_no
            LEFT JOIN departments d ON d.department_id = e.department_id
            {joins}
            {combine(where, "tr.end_date >= CURRENT_DATE AND tr.start_date <= :horizon_end")}
        """), {**params, "horizon_end": horizon_end}).fetchall()

        # ── Risk roster: trailing 30d vs prior 90d baseline ─────────────────
        risk_rows = s.execute(text(f"""
            SELECT ad.id_no, e.full_name, COALESCE(d.department_name, 'Unknown') AS dept,
                   COUNT(*) FILTER (WHERE ad.status = 'absent' AND ad.work_date > CURRENT_DATE - 30) AS recent_absent,
                   COUNT(*) FILTER (WHERE ad.status = 'absent' AND ad.work_date <= CURRENT_DATE - 30) AS base_absent,
                   COUNT(*) FILTER (WHERE ad.checkin_status = 'Late Arrival' AND ad.work_date > CURRENT_DATE - 30) AS recent_late,
                   COUNT(*) FILTER (WHERE ad.checkin_status = 'Late Arrival' AND ad.work_date <= CURRENT_DATE - 30) AS base_late
            FROM attendance_daily ad
            JOIN employees e ON e.id_no = ad.id_no
            LEFT JOIN departments d ON d.department_id = e.department_id
            {joins}
            {combine(where, 'ad.work_date > CURRENT_DATE - 120')}
            GROUP BY 1, 2, 3
        """), params).fetchall()

    # ── Attendance projection ───────────────────────────────────────────────
    att_proj = _project(att_series, horizon_weeks)
    projection: list[dict] = [{"label": lbl, "value": v, "actual": True} for lbl, v in att_series]
    if att_proj.get("fit"):
        a, b = att_proj["fit"]
        sigma = att_proj["sigma"]
        for i in range(1, horizon_weeks + 1):
            lbl = week_label_after(att_series, i)
            v = round(a + b * (len(att_series) - 1 + i), 1)
            projection.append({
                "label": lbl, "value": v, "actual": False,
                "bandLow": round(v - sigma, 1), "bandHigh": round(v + sigma, 1),
            })

    # ── Leave projection ────────────────────────────────────────────────────
    leave_proj = _project(leave_series, horizon_weeks)
    leave_forecast: list[dict] = [{"label": lbl, "value": v, "actual": True} for lbl, v in leave_series]
    if leave_proj.get("fit"):
        a, b = leave_proj["fit"]
        sigma = leave_proj["sigma"]
        for i in range(1, horizon_weeks + 1):
            lbl = week_label_after(leave_series, i)
            v = max(0.0, round(a + b * (len(leave_series) - 1 + i), 1))
            leave_forecast.append({
                "label": lbl, "value": v, "actual": False,
                "bandLow": round(max(0.0, v - sigma), 1), "bandHigh": round(v + sigma, 1),
            })

    # ── Coverage outlook grid ───────────────────────────────────────────────
    leave_dept_avg: dict[str, float] = {}
    dept_weeks: dict[str, list[float]] = {}
    for dept, _wk, n in leave_dept_rows:
        dept_weeks.setdefault(dept, []).append(float(n or 0))
    for dept, vals in dept_weeks.items():
        leave_dept_avg[dept] = sum(vals) / len(vals)

    # bucket scheduled trainings into outlook weeks (each row spans start..end)
    train_by_dept_week: dict[tuple[str, int], set] = {}
    week_starts = [(today - timedelta(days=today.weekday())) + timedelta(weeks=k) for k in range(outlook_weeks)]
    for dept, id_no, sd_, ed_ in raw_train:
        for k, ws in enumerate(week_starts):
            we = ws + timedelta(days=6)
            if sd_ <= we and ed_ >= ws:
                train_by_dept_week.setdefault((dept, k), set()).add(id_no)

    coverage = {"weeks": [ws.isoformat() for ws in week_starts], "departments": []}
    for dept, n_active in sorted(active_rows, key=lambda r: -r[1]):
        weeks = []
        for k in range(outlook_weeks):
            exp_leave = round(leave_dept_avg.get(dept, 0.0), 1)
            sched_train = len(train_by_dept_week.get((dept, k), set()))
            available = max(0, int(n_active) - int(math.ceil(exp_leave)) - sched_train)
            weeks.append({
                "week": week_starts[k].isoformat(),
                "expected_leave": exp_leave,
                "scheduled_training": sched_train,
                "available": available,
                "headcount": int(n_active),
            })
        coverage["departments"].append({"department": dept, "headcount": int(n_active), "weeks": weeks})

    # ── Risk roster ─────────────────────────────────────────────────────────
    risks = []
    for id_no, name, dept, r_abs, b_abs, r_late, b_late in risk_rows:
        recent = (r_abs or 0) + (r_late or 0) * 0.5
        base = ((b_abs or 0) + (b_late or 0) * 0.5) / 3.0  # 90d baseline → per-30d
        if recent < 3:
            continue
        ratio = round(recent / base, 2) if base > 0 else None
        risks.append({
            "id_no": id_no, "full_name": name, "department": dept,
            "recent_absent": r_abs or 0, "recent_late": r_late or 0,
            "baseline_per_30d": round(base, 1), "ratio": ratio,
            "score": round(recent * (2.0 if ratio and ratio >= 2 else 1.0), 1),
        })
    risks.sort(key=lambda r: r["score"], reverse=True)

    return {
        "as_of": today.isoformat(),
        "window_weeks": window_weeks,
        "horizon_weeks": horizon_weeks,
        "method": METHOD_NOTE,
        "projection": projection,
        "leave_forecast": leave_forecast,
        "coverage": coverage,
        "risks": risks[:12],
    }


# ── Small helpers ────────────────────────────────────────────────────────────
def combine(where: str, extra: str) -> str:
    if where:
        return where + " AND " + extra
    return "WHERE " + extra


def active_status_clause() -> str:
    from owl.rules.query_builder import get_active_statuses

    statuses = ", ".join(f"'{s_.lower()}'" for s_ in get_active_statuses())
    return f"LOWER(COALESCE((SELECT status_name FROM employee_statuses es WHERE es.status_id = e.status_id), '')) IN ({statuses})"


def week_label_after(series: list[tuple[str, float]], i: int) -> str:
    if series:
        last = date.fromisoformat(series[-1][0])
        return (last + timedelta(weeks=i)).isoformat()
    return (date.today() + timedelta(weeks=i)).isoformat()
