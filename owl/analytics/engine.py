"""Flexible analytics query engine over the rule-driven fact table and the
employee/leave/training tables. Summary mode aggregates by arbitrary dimensions;
records mode returns the underlying rows for drill-down.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from owl.load.database import get_session
from owl.rules.query_builder import get_active_statuses
from owl.analytics.dimensions import DIMENSIONS, dimension_expr, dimension_label
from owl.analytics.metrics import DOMAIN_METRICS

# ── Domain base definitions ───────────────────────────────────────────────────
DOMAIN_BASE: dict[str, dict] = {
    "attendance": {
        "from": "FROM attendance_daily ad JOIN employees e ON e.id_no = ad.id_no",
        "date_col": "ad.work_date",
        "record_select": (
            "ad.id_no, e.full_name, ad.work_date, ad.status, ad.checkin_time, "
            "ad.checkout_time, ad.checkin_status, ad.checkout_status, ad.minutes_worked"
        ),
        "record_columns": [
            "id_no", "full_name", "work_date", "status",
            "checkin_time", "checkout_time", "checkin_status", "checkout_status", "minutes_worked",
        ],
        "record_date_col": "ad.work_date",
        "default_metrics": ["attendance_rate", "present_days", "absent_days", "late_arrivals", "coverage"],
    },
    "leave": {
        "from": (
            "FROM leave_records lr JOIN employees e ON e.id_no = lr.id_no "
            "LEFT JOIN leave_types lt ON lt.leave_type_id = lr.leave_type_id"
        ),
        "date_col": "lr.start_date",
        "record_select": (
            "lr.record_id, lr.id_no, e.full_name, COALESCE(lt.leave_type_name, 'Unknown') AS leave_type, "
            "lr.start_date, COALESCE(lr.end_date, lr.start_date) AS end_date"
        ),
        "record_columns": ["record_id", "id_no", "full_name", "leave_type", "start_date", "end_date"],
        "record_date_col": "lr.start_date",
        "default_metrics": ["leave_records", "unique_staff", "avg_duration_days"],
    },
    "training": {
        "from": (
            "FROM employee_trainings tr JOIN employees e ON e.id_no = tr.id_no "
            "LEFT JOIN venues v ON v.venue_id = tr.venue_id "
            "LEFT JOIN consultants c ON c.consultant_id = tr.consultant_id"
        ),
        "date_col": "tr.start_date",
        "record_select": (
            "tr.training_id, tr.id_no, e.full_name, COALESCE(v.venue_name, 'Unknown') AS venue, "
            "COALESCE(c.consultant_name, 'Unknown') AS consultant, tr.start_date, tr.end_date, tr.title"
        ),
        "record_columns": ["training_id", "id_no", "full_name", "venue", "consultant", "start_date", "end_date", "title"],
        "record_date_col": "tr.start_date",
        "default_metrics": ["activities", "participants", "venues"],
    },
    "employees": {
        "from": "FROM employees e",
        "base_joins": [
            "LEFT JOIN employee_statuses es ON e.status_id = es.status_id",
            "LEFT JOIN departments d ON e.department_id = d.department_id",
            "LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id",
        ],
        "date_col": None,
        "record_select": (
            "e.id_no, e.full_name, e.sex, COALESCE(d.department_name, 'Unknown') AS department, "
            "COALESCE(gl.gl_name, 'Unknown') AS grade_level, COALESCE(es.status_name, 'Unknown') AS status"
        ),
        "record_columns": ["id_no", "full_name", "sex", "department", "grade_level", "status"],
        "record_date_col": None,
        "default_metrics": ["employees", "active"],
    },
}


def _metric_expr(domain: str, key: str) -> str | None:
    meta = DOMAIN_METRICS[domain].get(key)
    if not meta:
        return None
    expr = meta["expr"]
    if "{active_statuses}" in expr:
        quoted = ", ".join(f"'{s.lower()}'" for s in get_active_statuses())
        expr = expr.replace("{active_statuses}", quoted)
    return expr


def _collect_joins(cfg: dict, keys: list[str]) -> str:
    base = cfg.get("base_joins", [])
    if isinstance(base, str):
        base = [base] if base else []
    candidates = list(base) + [DIMENSIONS.get(k, {}).get("join", "") for k in keys]
    joins = []
    seen = set()
    for j in candidates:
        if j and j not in seen:
            seen.add(j)
            joins.append(j)
    return " ".join(joins)


def _build_filters(domain: str, cfg: dict, filters: dict, sd, ed, params: dict) -> str:
    clauses = []
    date_col = cfg["date_col"]
    if date_col and sd and ed:
        clauses.append(f"{date_col} BETWEEN :sd AND :ed")
        params["sd"] = sd
        params["ed"] = ed
    i = 0
    for key, values in (filters or {}).items():
        if not values:
            continue
        expr = dimension_expr(key, date_col or "ad.work_date")
        if not expr:
            continue
        phs = []
        for v in values:
            pname = f"f{i}"
            params[pname] = v
            phs.append(f":{pname}")
            i += 1
        clauses.append(f"{expr} IN ({', '.join(phs)})")
    return ("WHERE " + " AND ".join(clauses)) if clauses else ""


def _previous_period(sd: str, ed: str):
    if not sd or not ed:
        return None, None
    s = date.fromisoformat(sd)
    e = date.fromisoformat(ed)
    length = (e - s).days + 1
    prev_end = s - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    return prev_start.isoformat(), prev_end.isoformat()


def run_explore(
    domain: str,
    metrics: list[str] | None = None,
    group_by: list[str] | None = None,
    filters: dict | None = None,
    date_range: dict | None = None,
    compare: str | None = None,
    mode: str = "summary",
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "",
    sort_dir: str = "desc",
    search: str = "",
) -> dict:
    if domain not in DOMAIN_BASE:
        raise ValueError(f"Unknown domain '{domain}'")
    cfg = DOMAIN_BASE[domain]
    metric_defs = DOMAIN_METRICS[domain]
    metrics = [m for m in (metrics or cfg["default_metrics"]) if m in metric_defs] or cfg["default_metrics"]
    group_by = [g for g in (group_by or []) if g in DIMENSIONS or g in ("day", "week", "month", "quarter")]

    sd = (date_range or {}).get("start")
    ed = (date_range or {}).get("end")

    with get_session() as s:
        if mode == "records":
            result = _run_records(s, cfg, filters, sd, ed, page, page_size, search, sort_by, sort_dir)
        else:
            result = _run_summary(s, domain, cfg, metric_defs, metrics, group_by, filters, sd, ed,
                                  page, page_size, sort_by, sort_dir)

        # Totals (scope-level KPIs)
        params = {}
        where = _build_filters(domain, cfg, filters, sd, ed, params)
        joins = _collect_joins(cfg, list((filters or {}).keys()) + group_by)
        select_metrics = ", ".join(f"{_metric_expr(domain, m)} AS \"{m}\"" for m in metrics)
        totals_row = s.execute(
            text(f"SELECT {select_metrics} {cfg['from']} {joins} {where}"), params
        ).mappings().fetchone()
        result["totals"] = dict(totals_row) if totals_row else {}

        # Period comparison (totals)
        if compare == "previous":
            psd, ped = _previous_period(sd, ed)
            if psd and ped:
                pparams = {}
                pwhere = _build_filters(domain, cfg, filters, psd, ped, pparams)
                prow = s.execute(
                    text(f"SELECT {select_metrics} {cfg['from']} {joins} {pwhere}"), pparams
                ).mappings().fetchone()
                result["previous_totals"] = dict(prow) if prow else {}
                result["previous_range"] = {"start": psd, "end": ped}

    return result


def _run_summary(s, domain, cfg, metric_defs, metrics, group_by, filters, sd, ed, page, page_size, sort_by, sort_dir):
    date_col = cfg["date_col"] or "ad.work_date"
    joins = _collect_joins(cfg, list((filters or {}).keys()) + group_by)
    params = {}
    where = _build_filters(domain, cfg, filters, sd, ed, params)

    dim_exprs = [(g, dimension_expr(g, date_col)) for g in group_by]
    select_parts = [f"{expr} AS \"{key}\"" for key, expr in dim_exprs]
    select_parts += [f"{_metric_expr(domain, m)} AS \"{m}\"" for m in metrics]
    select_sql = ", ".join(select_parts)

    group_sql = f"GROUP BY {', '.join(expr for _, expr in dim_exprs)}" if dim_exprs else ""

    # Ordering
    order_col = None
    if sort_by:
        if sort_by in [g for g, _ in dim_exprs]:
            order_col = f'"{sort_by}"'
        elif sort_by in metrics:
            order_col = f'"{sort_by}"'
    if not order_col and metrics:
        order_col = f'"{metrics[0]}"'
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    order_sql = f"ORDER BY {order_col} {direction}" if order_col else ""

    # Total group count
    if dim_exprs:
        count_sql = f"SELECT COUNT(*) FROM (SELECT 1 {cfg['from']} {joins} {where} {group_sql}) t"
    else:
        count_sql = f"SELECT 1 {cfg['from']} {joins} {where}"
    total = s.execute(text(count_sql), params).scalar() if dim_exprs else 1

    offset = (page - 1) * page_size if page_size and page_size > 0 else 0
    limit_sql = f"LIMIT {int(page_size)} OFFSET {int(offset)}" if page_size and page_size > 0 else ""
    rows = s.execute(
        text(f"SELECT {select_sql} {cfg['from']} {joins} {where} {group_sql} {order_sql} {limit_sql}"),
        params,
    ).mappings().all()

    columns = [{"key": g, "label": dimension_label(g)} for g in group_by]
    columns += [{"key": m, "label": metric_defs[m]["label"], "type": metric_defs[m].get("type", "int")} for m in metrics]
    return {
        "mode": "summary",
        "columns": columns,
        "groups": [dict(r) for r in rows],
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
    }


def _run_records(s, cfg, filters, sd, ed, page, page_size, search, sort_by, sort_dir):
    # records mode: needs employee joins only
    joins = _collect_joins(cfg, list((filters or {}).keys()))
    params = {}
    # date filter uses the domain's record date col, not the employee one
    clauses = []
    if cfg["record_date_col"] and sd and ed:
        clauses.append(f"{cfg['record_date_col']} BETWEEN :sd AND :ed")
        params["sd"] = sd
        params["ed"] = ed
    i = 0
    for key, values in (filters or {}).items():
        if not values:
            continue
        expr = dimension_expr(key, cfg["record_date_col"] or "e.id_no")
        if not expr:
            continue
        phs = []
        for v in values:
            pname = f"r{i}"
            params[pname] = v
            phs.append(f":{pname}")
            i += 1
        clauses.append(f"{expr} IN ({', '.join(phs)})")
    if search and search.strip():
        q = search.strip().lower()
        params["q"] = f"%{q}%"
        text_cols = [c for c in cfg["record_columns"]]
        clauses.append("(" + " OR ".join(f"LOWER(COALESCE(CAST({c} AS text),'')) LIKE :q" for c in text_cols) + ")")
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    order_col = sort_by if sort_by in cfg["record_columns"] else (cfg["record_date_col"] or cfg["record_columns"][0])
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"

    total = s.execute(text(f"SELECT COUNT(*) {cfg['from']} {joins} {where_sql}"), params).scalar()
    offset = (page - 1) * page_size if page_size and page_size > 0 else 0
    limit_sql = f"LIMIT {int(page_size)} OFFSET {int(offset)}" if page_size and page_size > 0 else ""
    rows = s.execute(
        text(f"SELECT {cfg['record_select']} {cfg['from']} {joins} {where_sql} ORDER BY {order_col} {direction} {limit_sql}"),
        params,
    ).mappings().all()

    return {
        "mode": "records",
        "columns": [{"key": c, "label": c.replace("_", " ").title()} for c in cfg["record_columns"]],
        "records": [dict(r) for r in rows],
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
    }


def get_dimension_options() -> dict:
    """Distinct values for each attribute dimension."""
    options = {}
    with get_session() as s:
        for key, meta in DIMENSIONS.items():
            expr = meta["expr"]
            rows = s.execute(text(
                f"SELECT DISTINCT {expr} AS v FROM employees e {meta['join']} ORDER BY 1"
            )).fetchall()
            options[key] = [r[0] for r in rows if r[0] is not None]
    return options
