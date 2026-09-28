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
# search_exprs use fully-qualified columns: several record columns (id_no)
# exist in more than one joined table and bare references are ambiguous.
# record_filter_cols whitelists which record columns are filterable and how
# each maps to SQL.
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
        "search_exprs": [
            "CAST(ad.id_no AS text)", "e.full_name", "ad.status",
            "ad.checkin_status", "ad.checkout_status",
        ],
        "record_filter_cols": {
            "status": "ad.status",
            "checkin_status": "ad.checkin_status",
            "checkout_status": "ad.checkout_status",
        },
        "record_date_cols": {"work_date": "ad.work_date"},
        "default_metrics": ["attendance_rate", "present_days", "absent_days", "late_arrivals", "coverage"],
    },
    "leave": {
        "from": (
            "FROM leave_records lr JOIN employees e ON e.id_no = lr.id_no "
            "LEFT JOIN leave_types lt ON lt.leave_type_id = lr.leave_type_id "
            "LEFT JOIN departments d ON d.department_id = e.department_id "
            "LEFT JOIN grade_levels gl ON gl.gl_id = e.gl_id"
        ),
        "date_col": "lr.start_date",
        "record_select": (
            "lr.record_id, lr.id_no, e.full_name, COALESCE(lt.leave_type_name, 'Unknown') AS leave_type, "
            "COALESCE(d.department_name, 'Unknown') AS department, "
            "COALESCE(gl.gl_name, 'Unknown') AS grade_level, "
            "lr.start_date, COALESCE(lr.end_date, lr.start_date) AS end_date"
        ),
        "record_columns": ["record_id", "id_no", "full_name", "leave_type", "department", "grade_level", "start_date", "end_date"],
        "record_date_col": "lr.start_date",
        "search_exprs": [
            "CAST(lr.id_no AS text)", "e.full_name",
            "COALESCE(lt.leave_type_name, 'Unknown')",
            "COALESCE(d.department_name, 'Unknown')",
            "COALESCE(gl.gl_name, 'Unknown')",
            "CAST(lr.start_date AS text)", "CAST(COALESCE(lr.end_date, lr.start_date) AS text)",
        ],
        "record_filter_cols": {
            "leave_type": "COALESCE(lt.leave_type_name, 'Unknown')",
            "department": "COALESCE(d.department_name, 'Unknown')",
            "grade_level": "COALESCE(gl.gl_name, 'Unknown')",
        },
        # Date columns the UI may narrow with sub-ranges
        "record_date_cols": {
            "start_date": "lr.start_date",
            "end_date": "COALESCE(lr.end_date, lr.start_date)",
        },
        "default_metrics": ["leave_records", "unique_staff", "avg_duration_days"],
    },
    "training": {
        "from": (
            "FROM employee_trainings tr JOIN employees e ON e.id_no = tr.id_no "
            "LEFT JOIN venues v ON v.venue_id = tr.venue_id "
            "LEFT JOIN consultants c ON c.consultant_id = tr.consultant_id "
            "LEFT JOIN departments d ON d.department_id = e.department_id "
            "LEFT JOIN grade_levels gl ON gl.gl_id = e.gl_id"
        ),
        "date_col": "tr.start_date",
        "record_select": (
            "tr.training_id, tr.id_no, e.full_name, COALESCE(v.venue_name, 'Unknown') AS venue, "
            "COALESCE(c.consultant_name, 'Unknown') AS consultant, "
            "COALESCE(d.department_name, 'Unknown') AS department, "
            "COALESCE(gl.gl_name, 'Unknown') AS grade_level, "
            "tr.start_date, tr.end_date, tr.title"
        ),
        "record_columns": ["training_id", "id_no", "full_name", "venue", "consultant", "department", "grade_level", "start_date", "end_date", "title"],
        "record_date_col": "tr.start_date",
        "search_exprs": [
            "CAST(tr.id_no AS text)", "e.full_name",
            "COALESCE(v.venue_name, 'Unknown')", "COALESCE(c.consultant_name, 'Unknown')", "tr.title",
            "COALESCE(d.department_name, 'Unknown')",
            "COALESCE(gl.gl_name, 'Unknown')",
        ],
        "record_filter_cols": {
            "venue": "COALESCE(v.venue_name, 'Unknown')",
            "consultant": "COALESCE(c.consultant_name, 'Unknown')",
            "department": "COALESCE(d.department_name, 'Unknown')",
            "grade_level": "COALESCE(gl.gl_name, 'Unknown')",
        },
        "record_date_cols": {
            "start_date": "tr.start_date",
            "end_date": "tr.end_date",
        },
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
        "search_exprs": [
            "CAST(e.id_no AS text)", "e.full_name", "e.sex",
            "COALESCE(d.department_name, 'Unknown')",
            "COALESCE(gl.gl_name, 'Unknown')",
            "COALESCE(es.status_name, 'Unknown')",
        ],
        "record_filter_cols": {
            "department": "COALESCE(d.department_name, 'Unknown')",
            "grade_level": "COALESCE(gl.gl_name, 'Unknown')",
            "status": "COALESCE(es.status_name, 'Unknown')",
            "sex": "e.sex",
        },
        "record_date_cols": {},
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


def _join_alias(join_sql: str) -> str:
    """Alias a JOIN clause introduces: 'LEFT JOIN departments d ON ...' -> 'd'."""
    parts = (join_sql or "").split()
    for i, p in enumerate(parts):
        if p.upper() == "JOIN" and i + 1 < len(parts):
            nxt = parts[i + 2] if i + 2 < len(parts) else ""
            return parts[i + 1] if nxt.upper() == "ON" else nxt
    return join_sql


def _from_aliases(from_sql: str) -> set[str]:
    """Table aliases already bound by a FROM clause (base table + its JOINs)."""
    parts = (from_sql or "").split()
    out: set[str] = set()
    if (
        len(parts) >= 3
        and parts[0].upper() == "FROM"
        and parts[2].upper() not in ("JOIN", "LEFT", "RIGHT", "INNER", "FULL", "CROSS", "WHERE", "ON")
    ):
        out.add(parts[2])
    for i, p in enumerate(parts):
        if p.upper() == "JOIN" and i + 1 < len(parts):
            out.add(_join_alias(" ".join(parts[i:])))
    return out


def _collect_joins(cfg: dict, keys: list[str]) -> str:
    base = cfg.get("base_joins", [])
    if isinstance(base, str):
        base = [base] if base else []
    # Dedupe by introduced alias, not exact text: domain FROM clauses bind the
    # same aliases (d, gl, ...) with different ON-condition wording, and
    # re-joining an alias raises DuplicateAlias.
    taken = _from_aliases(cfg.get("from", ""))
    for j in base:
        taken.add(_join_alias(j))
    joins = list(base)
    for k in keys:
        j = DIMENSIONS.get(k, {}).get("join", "")
        if not j:
            continue
        alias = _join_alias(j)
        if alias in taken:
            continue
        taken.add(alias)
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
    record_filters: dict | None = None,
    date_sub_ranges: dict | None = None,
    date_filter_mode: str = "overlap",
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
            result = _run_records(s, cfg, filters, sd, ed, page, page_size, search, sort_by, sort_dir,
                                   record_filters, date_sub_ranges, date_filter_mode, domain)
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


def _run_records(s, cfg, filters, sd, ed, page, page_size, search, sort_by, sort_dir,
                 record_filters=None, date_sub_ranges=None, date_filter_mode: str = "overlap", domain: str = ""):
    joins = _collect_joins(cfg, list((filters or {}).keys()))
    params: dict = {}
    clauses: list[str] = []

    # Date windows
    # Global scope window (record_date_col BETWEEN sd AND ed)
    # Per-column sub-ranges: for leave/training treated as a single overlap
    # interval unrestricted by the global range; for attendance kept as BETWEEN
    # and clamped to the global scope.
    date_cols: dict[str, str] = cfg.get("record_date_cols", {})
    windows: list[tuple[str, str, str]] = []  # (sql_expr, lo, hi)
    if sd and ed and cfg.get("record_date_col"):
        windows.append((cfg["record_date_col"], sd, ed))
    # Collect leave/training sub-ranges for overlap handling
    sub_los: list[str] = []
    sub_his: list[str] = []
    for col_key, rng in (date_sub_ranges or {}).items():
        if not rng or not rng.get("start") or not rng.get("end"):
            continue
        if domain in ("leave", "training") and col_key in ("start_date", "end_date", "date_range"):
            sub_los.append(rng["start"])
            sub_his.append(rng["end"])
            continue
        expr = date_cols.get(col_key)
        if not expr:
            continue
        sub_s, sub_e = rng["start"], rng["end"]
        lo = max(sd, sub_s) if sd else sub_s
        hi = min(ed, sub_e) if ed else sub_e
        if lo > hi:
            continue
        windows.append((expr, lo, hi))
    # Single window for leave/training
    if sub_los:
        lo = min(sub_los)
        hi = max(sub_his)
        if date_filter_mode == "strict":
            if domain == "leave":
                clauses.append("lr.start_date >= :sub_lo AND COALESCE(lr.end_date, lr.start_date) <= :sub_hi")
            else:
                clauses.append("tr.start_date >= :sub_lo AND tr.end_date <= :sub_hi")
        else:
            if domain == "leave":
                clauses.append("lr.start_date <= :sub_hi AND COALESCE(lr.end_date, lr.start_date) >= :sub_lo")
            else:
                clauses.append("tr.start_date <= :sub_hi AND tr.end_date >= :sub_lo")
        params["sub_lo"] = lo
        params["sub_hi"] = hi
    i = 0
    for expr, lo, hi in windows:
        if not expr:
            continue
        clauses.append(f"{expr} BETWEEN :dw{i}s AND :dw{i}e")
        params[f"dw{i}s"] = lo
        params[f"dw{i}e"] = hi
        i += 1
    # The primary window (first) defines the filter-option scope bounds
    lo, hi = (windows[0][1], windows[0][2]) if windows else (None, None)

    def _dimension_clauses(p: dict, prefix: str) -> list[str]:
        cs: list[str] = []
        i = 0
        for key, values in (filters or {}).items():
            if not values:
                continue
            expr = dimension_expr(key, cfg["record_date_col"] or "e.id_no")
            if not expr:
                continue
            phs = []
            for v in values:
                pname = f"{prefix}{i}"
                p[pname] = v
                phs.append(f":{pname}")
                i += 1
            cs.append(f"{expr} IN ({', '.join(phs)})")
        return cs

    clauses.extend(_dimension_clauses(params, "r"))

    # Whitelisted record-column filters (status, leave_type, venue, ...)
    rf_cols: dict[str, str] = cfg.get("record_filter_cols", {})
    i = 0
    for key, values in (record_filters or {}).items():
        expr = rf_cols.get(key)
        if not expr or not values:
            continue
        phs = []
        for v in values:
            pname = f"rf{i}"
            params[pname] = v
            phs.append(f":{pname}")
            i += 1
        clauses.append(f"{expr} IN ({', '.join(phs)})")

    if search and search.strip():
        q = search.strip().lower()
        params["q"] = f"%{q}%"
        exprs = cfg.get("search_exprs") or [f"CAST({c} AS text)" for c in cfg["record_columns"]]
        clauses.append("(" + " OR ".join(f"LOWER(COALESCE({e}, '')) LIKE :q" for e in exprs) + ")")
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    if sort_by == "date_range" and "start_date" in cfg["record_columns"]:
        # UI's combined period column sorts by period start
        sort_by = "start_date"
    order_col = sort_by if sort_by in cfg["record_columns"] else (cfg["record_date_col"] or cfg["record_columns"][0])
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"

    total = s.execute(text(f"SELECT COUNT(*) {cfg['from']} {joins} {where_sql}"), params).scalar()
    offset = (page - 1) * page_size if page_size and page_size > 0 else 0
    limit_sql = f"LIMIT {int(page_size)} OFFSET {int(offset)}" if page_size and page_size > 0 else ""
    rows = s.execute(
        text(f"SELECT {cfg['record_select']} {cfg['from']} {joins} {where_sql} ORDER BY {order_col} {direction} {limit_sql}"),
        params,
    ).mappings().all()

    # Enrich leave/training with working-day-aware days_used / days_unused (relative to today)
    if domain in ("leave", "training") and rows:
        from owl.rules.query_builder import get_working_weekdays

        try:
            from owl.rules.engine import get_rule as _gr2
            hd2 = _gr2("holidays", {}).get("dates", [])
        except Exception:
            hd2 = []
        hs2: set[date] = set()
        for _d2 in hd2:
            try:
                hs2.add(date.fromisoformat(str(_d2)))
            except Exception:
                pass
        wdows = set(get_working_weekdays())

        def _cnt_working(a: date, b: date) -> int:
            if not a or not b or a > b:
                return 0
            n = 0
            cur2 = a
            while cur2 <= b:
                if (cur2.weekday() + 1) in wdows and cur2 not in hs2:
                    n += 1
                cur2 += timedelta(days=1)
            return n

        today2 = date.today()
        enriched: list[dict] = []
        for _r in rows:
            _d = dict(_r)
            _s = _d.get("start_date")
            _e = _d.get("end_date")
            if _s and _e:
                total_w = _cnt_working(_s, _e)
                if today2 < _s:
                    used_w = 0
                elif today2 > _e:
                    used_w = total_w
                else:
                    used_w = _cnt_working(_s, today2)
                _d["days_used"] = used_w
                _d["days_unused"] = total_w - used_w
                _d["total_days"] = total_w
            else:
                _d["days_used"] = 0
                _d["days_unused"] = 0
                _d["total_days"] = 0
            enriched.append(_d)
        rows = enriched  # type: ignore[assignment]

    # Distinct values per filterable record column, within scope + date window
    # (ignores search and the record filters themselves, so every option stays
    # reachable — same pattern as the dashboard's employee-summary filters).
    filter_options: dict[str, list[str]] = {}
    for key, expr in rf_cols.items():
        opt_params: dict = {}
        opt_clauses = _dimension_clauses(opt_params, "o")
        if cfg["record_date_col"] and lo and hi:
            opt_clauses.insert(0, f"{cfg['record_date_col']} BETWEEN :osd AND :oed")
            opt_params["osd"] = lo
            opt_params["oed"] = hi
        opt_where = ("WHERE " + " AND ".join(opt_clauses)) if opt_clauses else ""
        try:
            opt_rows = s.execute(
                text(f"SELECT DISTINCT {expr} {cfg['from']} {joins} {opt_where} ORDER BY 1 LIMIT 300"),
                opt_params,
            ).fetchall()
            filter_options[key] = [str(r[0]) for r in opt_rows if r[0] is not None]
        except Exception:  # noqa: BLE001 — options are a convenience, never fail the query
            filter_options[key] = []

    return {
        "mode": "records",
        "columns": [{"key": c, "label": c.replace("_", " ").title()} for c in cfg["record_columns"]],
        "records": [dict(r) for r in rows],
        "filter_options": filter_options,
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
    }


# Range-trend subjects: period table + staff id + span columns behind the
# staff-over-time charts. The end expression keeps open-ended spans counted.
_TREND_SUBJECTS = {
    "leave": {
        "table": "leave_records",
        "alias": "lr",
        "id_col": "lr.id_no",
        "span_start": "lr.start_date",
        "span_end": "COALESCE(lr.end_date, lr.start_date)",
    },
    "training": {
        "table": "employee_trainings",
        "alias": "tr",
        "id_col": "tr.id_no",
        "span_start": "tr.start_date",
        "span_end": "COALESCE(tr.end_date, tr.start_date)",
    },
}


def _range_trend(domain: str, start: str, end: str, granularity: str = "month", filters: dict | None = None) -> dict:
    """Staff-over-time time series: per bucket, per department, the distinct
    staff whose span overlaps the bucket.

    Granularity is 'day' (one bucket per date) or 'month' (calendar months).
    Only global scope dimension filters apply — record-table filters do not.
    """
    if domain not in _TREND_SUBJECTS:
        raise ValueError(f"Unknown trend domain '{domain}'")
    if granularity not in ("day", "month"):
        raise ValueError(f"Unknown granularity '{granularity}'")
    try:
        sd = date.fromisoformat(start)
        ed = date.fromisoformat(end)
    except (ValueError, TypeError):
        raise ValueError("start/end must be YYYY-MM-DD dates")
    if sd > ed:
        raise ValueError("start must not be after end")
    if (ed - sd).days > 730:
        raise ValueError("range too large (max 2 years)")
    subj = _TREND_SUBJECTS[domain]
    cfg = DOMAIN_BASE["leave" if domain == "leave" else "training"]
    step = "1 day" if granularity == "day" else "1 month"
    # NOTE: CAST() instead of :: — SQLAlchemy text() chokes on :: casts.
    first = "CAST(:sd AS date)" if granularity == "day" else "date_trunc('month', CAST(:sd AS date))"

    params: dict = {"sd": sd.isoformat(), "ed": ed.isoformat()}
    # Joins for the series dimension + scope filters, deduped by alias.
    # (The shared _collect_joins can't be used: it assumes the subject FROM
    # is present, but here the bucket series drives the query.)
    join_parts: list[str] = []
    seen_aliases = {"b", subj["alias"], "e"}
    for k in ["department"] + list((filters or {}).keys()):
        j = DIMENSIONS.get(k, {}).get("join", "")
        if not j:
            continue
        if _join_alias(j) in seen_aliases:
            continue
        seen_aliases.add(_join_alias(j))
        join_parts.append(j)
    joins = " ".join(join_parts)
    clauses: list[str] = []
    i = 0
    for key, values in (filters or {}).items():
        if not values:
            continue
        expr = dimension_expr(key, cfg["date_col"])
        if not expr:
            continue
        phs = []
        for v in values:
            pname = f"f{i}"
            params[pname] = v
            phs.append(f":{pname}")
            i += 1
        clauses.append(f"{expr} IN ({', '.join(phs)})")
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    # A span counts toward every bucket it overlaps.
    # NOTE: the subject's FROM is not reused here — the bucket series
    # drives the query and the period table joins to it, not the other way round.
    t, a = subj["table"], subj["alias"]
    sql = (
        "SELECT CAST(b AS date) AS bucket, "
        "COALESCE(d.department_name, 'Unknown') AS department, "
        f"COUNT(DISTINCT {subj['id_col']}) AS staff "
        f"FROM generate_series(({first}), CAST(:ed AS date), CAST('{step}' AS interval)) AS b "
        f"JOIN {t} {a} ON {subj['span_start']} <= CAST(b + "
        f"CAST('{step}' AS interval) - INTERVAL '1 day' AS date) "
        f"AND {subj['span_end']} >= CAST(b AS date) "
        f"JOIN employees e ON e.id_no = {a}.id_no {joins} {where_sql} "
        "GROUP BY 1, 2 ORDER BY 1, 2"
    )
    with get_session() as s:
        rows = s.execute(text(sql), params).mappings().all()
    return {
        "domain": domain,
        "granularity": granularity,
        "start": sd.isoformat(),
        "end": ed.isoformat(),
        "rows": [{"bucket": r["bucket"].isoformat(), "department": r["department"], "staff": int(r["staff"])} for r in rows],
    }


def leave_trend(start: str, end: str, granularity: str = "month", filters: dict | None = None) -> dict:
    """Staff-on-leave time series (see _range_trend)."""
    return _range_trend("leave", start, end, granularity, filters)


def training_trend(start: str, end: str, granularity: str = "month", filters: dict | None = None) -> dict:
    """Staff-in-training time series (see _range_trend)."""
    return _range_trend("training", start, end, granularity, filters)


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
