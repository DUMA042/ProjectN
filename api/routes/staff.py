"""Staff endpoints — paginated directory + employee profile + attendance stats."""

import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.dependencies import get_db

router = APIRouter(tags=["staff"])


@router.get("/statuses")
def list_statuses():
    """All distinct employee statuses in the database (full lookup list)."""
    from ui.lib.queries import get_statuses

    return get_statuses()


from owl.analytics.classification import (
    DAY_NAMES,
    WEEKDAY_SHORT,
    MONTH_SHORT,
    classify_checkin as _classify_checkin,
    classify_checkout as _classify_checkout,
    classify_day as _classify_day_shared,
    fmt_hours as _fmt_hours,
    hm_to_min as _hm_to_min,
)


def _classify_day(d, leave_ranges, training_ranges, swipe_dates, holiday_set, is_active, today,
                  working_dows, leave_overrides_training):
    """Backwards-compatible wrapper around the shared classifier."""
    ctx = {
        "working_dows": working_dows,
        "holiday_set": holiday_set,
        "leave_overrides_training": leave_overrides_training,
    }
    return _classify_day_shared(d, leave_ranges, training_ranges, swipe_dates, ctx, is_active, today)


def _paginate_records(rows, columns, numeric_columns, page, page_size, search, sort_by, sort_dir, filters):
    filter_options = {}
    for col in columns:
        filter_options[col] = sorted(
            {str(r[col]) for r in rows if r.get(col) not in (None, "")},
            key=lambda s: s.lower(),
        )
    for col, selected in (filters or {}).items():
        if not selected:
            continue
        sel = {str(v) for v in selected}
        rows = [r for r in rows if str(r.get(col)) in sel]
    if search and search.strip():
        q = search.strip().lower()
        rows = [r for r in rows if any(q in str(v).lower() for v in r.values())]
    if sort_by not in columns:
        sort_by = columns[0]
    reverse = str(sort_dir).lower() == "desc"
    non_null = [r for r in rows if r.get(sort_by) not in (None, "")]
    nulls = [r for r in rows if r.get(sort_by) in (None, "")]
    if sort_by in numeric_columns:
        non_null.sort(key=lambda r: float(r[sort_by]), reverse=reverse)
    else:
        non_null.sort(key=lambda r: str(r[sort_by]).lower(), reverse=reverse)
    rows = non_null + nulls
    total = len(rows)
    if page_size and page_size > 0:
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        items = rows[(page - 1) * page_size:(page - 1) * page_size + page_size]
    else:
        page = 1
        items = rows
    return {"items": items, "total": total, "page": page, "page_size": page_size, "filter_options": filter_options}


@router.get("/staff")
def staff_list(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    search: str = Query("", max_length=100),
    department: str = Query("", max_length=100),
):
    offset = (page - 1) * size
    params = {"offset": offset, "limit": size}

    where_clauses = []
    if search:
        where_clauses.append(
            "(LOWER(e.full_name) LIKE :search OR LOWER(e.id_no) LIKE :search)"
        )
        params["search"] = f"%{search.lower()}%"
    if department:
        where_clauses.append("LOWER(d.department_name) = :dept")
        params["dept"] = department.lower()

    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

    sql = f"""
        SELECT e.id_no, e.full_name, e.sex,
               d.department_name, r.rank_name, gl.gl_name,
               es.status_name, e.geographical_zone,
               e.date_of_last_deployment, e.remark
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN ranks r ON e.rank_id = r.rank_id
        LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
        LEFT JOIN employee_statuses es ON e.status_id = es.status_id
        WHERE {where_sql}
        ORDER BY e.full_name
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(sql), params).fetchall()
    total = db.execute(text(f"SELECT COUNT(*) FROM employees e WHERE {where_sql}"), {k: v for k, v in params.items() if k != "offset" and k != "limit"}).scalar()

    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id_no": r[0], "full_name": r[1], "sex": r[2],
                "department": r[3], "rank": r[4], "grade_level": r[5],
                "status": r[6], "geographical_zone": r[7],
                "date_of_last_deployment": r[8].isoformat() if r[8] else None,
                "remark": r[9],
            }
            for r in rows
        ],
    }


@router.get("/staff/{id_no}")
def staff_profile(id_no: str, db: Session = Depends(get_db)):
    emp = db.execute(
        text("""
            SELECT e.id_no, e.full_name, e.sex, e.geographical_zone,
                   d.department_name, r.rank_name, gl.gl_name,
                   es.status_name, et.emp_type_name,
                   e.date_of_last_deployment, e.phone_number, e.remark
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.department_id
            LEFT JOIN ranks r ON e.rank_id = r.rank_id
            LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
            LEFT JOIN employee_statuses es ON e.status_id = es.status_id
            LEFT JOIN employment_types et ON e.emp_type_id = et.emp_type_id
            WHERE e.id_no = :id_no
        """),
        {"id_no": id_no},
    ).fetchone()

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "id_no": emp[0], "full_name": emp[1], "sex": emp[2],
        "geographical_zone": emp[3], "department": emp[4], "rank": emp[5],
        "grade_level": emp[6], "status": emp[7], "employment_type": emp[8],
        "date_of_last_deployment": emp[9].isoformat() if emp[9] else None,
        "phone_number": emp[10], "remark": emp[11],
    }


@router.get("/employees/{id_no}/detail")
def employee_detail(id_no: str, db: Session = Depends(get_db)):
    emp = db.execute(
        text("""
            SELECT e.id_no, e.full_name, e.sex, e.geographical_zone,
                   d.department_name, r.rank_name, gl.gl_name,
                   es.status_name, et.emp_type_name,
                   e.date_of_last_deployment, e.phone_number, e.remark
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.department_id
            LEFT JOIN ranks r ON e.rank_id = r.rank_id
            LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
            LEFT JOIN employee_statuses es ON e.status_id = es.status_id
            LEFT JOIN employment_types et ON e.emp_type_id = et.emp_type_id
            WHERE e.id_no = :id_no
        """),
        {"id_no": id_no},
    ).fetchone()

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    swipes = db.execute(
        text("""
            SELECT cs.swipe_id, cs.swipe_time,
                   COALESCE(l.location_name, 'Unknown') AS location
            FROM employee_card_swipes cs
            LEFT JOIN locations l ON cs.location_id = l.location_id
            WHERE cs.id_no = :id_no
            ORDER BY cs.swipe_time DESC LIMIT 20
        """),
        {"id_no": id_no},
    ).fetchall()

    leaves = db.execute(
        text("""
            SELECT lr.record_id, lt.leave_type_name,
                   lr.start_date, lr.end_date
            FROM leave_records lr
            LEFT JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
            WHERE lr.id_no = :id_no
            ORDER BY lr.start_date DESC LIMIT 20
        """),
        {"id_no": id_no},
    ).fetchall()

    trainings = db.execute(
        text("""
            SELECT et.training_id,
                   COALESCE(v.venue_name, 'Unknown') AS venue,
                   COALESCE(c.consultant_name, 'Unknown') AS consultant,
                   et.start_date, et.end_date, et.title
            FROM employee_trainings et
            LEFT JOIN venues v ON et.venue_id = v.venue_id
            LEFT JOIN consultants c ON et.consultant_id = c.consultant_id
            WHERE et.id_no = :id_no
            ORDER BY et.start_date DESC LIMIT 20
        """),
        {"id_no": id_no},
    ).fetchall()

    return {
        "id_no": emp[0],
        "full_name": emp[1],
        "sex": emp[2],
        "geographical_zone": emp[3],
        "department": emp[4],
        "rank": emp[5],
        "grade_level": emp[6],
        "status": emp[7],
        "employment_type": emp[8],
        "date_of_last_deployment": emp[9].isoformat() if emp[9] else None,
        "phone_number": emp[10],
        "remark": emp[11],
        "card_swipes": [
            {
                "swipe_id": s[0],
                "swipe_time": s[1].isoformat() if s[1] else None,
                "location": s[2],
            }
            for s in swipes
        ],
        "leave_records": [
            {
                "record_id": l[0],
                "leave_type_name": l[1],
                "start_date": l[2].isoformat() if l[2] else None,
                "end_date": l[3].isoformat() if l[3] else None,
            }
            for l in leaves
        ],
        "training_records": [
            {
                "training_id": t[0],
                "venue": t[1],
                "consultant": t[2],
                "start_date": t[3].isoformat() if t[3] else None,
                "end_date": t[4].isoformat() if t[4] else None,
                "title": t[5],
            }
            for t in trainings
        ],
    }


@router.get("/employees/{id_no}/attendance-stats")
def employee_attendance_stats(
    id_no: str,
    start_date: str = Query("", description="Start date YYYY-MM-DD"),
    end_date: str = Query("", description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    emp = db.execute(
        text("""
            SELECT e.id_no, e.full_name, e.sex, e.geographical_zone,
                   d.department_name, r.rank_name, gl.gl_name,
                   es.status_name, et.emp_type_name,
                   e.phone_number
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.department_id
            LEFT JOIN ranks r ON e.rank_id = r.rank_id
            LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
            LEFT JOIN employee_statuses es ON e.status_id = es.status_id
            LEFT JOIN employment_types et ON e.emp_type_id = et.emp_type_id
            WHERE e.id_no = :id_no
        """),
        {"id_no": id_no},
    ).fetchone()

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    today = date.today()
    if start_date and end_date:
        try:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")
        if sd > ed:
            raise HTTPException(status_code=422, detail="start_date must be <= end_date")
    elif start_date or end_date:
        raise HTTPException(status_code=422, detail="Both start_date and end_date must be provided together")
    else:
        sd = today.replace(day=1)
        ed = today

    swipes_raw = db.execute(
        text("""
            SELECT DATE(swipe_time) AS swipe_date, MIN(swipe_time) AS checkin, MAX(swipe_time) AS checkout
            FROM employee_card_swipes
            WHERE id_no = :id_no AND swipe_time::date BETWEEN :sd AND :ed
            GROUP BY DATE(swipe_time)
        """),
        {"id_no": id_no, "sd": sd, "ed": ed},
    ).fetchall()

    leave_raw = db.execute(
        text("""
            SELECT start_date, COALESCE(end_date, start_date) AS end_date
            FROM leave_records
            WHERE id_no = :id_no AND start_date <= :ed AND COALESCE(end_date, start_date) >= :sd
        """),
        {"id_no": id_no, "sd": sd, "ed": ed},
    ).fetchall()

    training_raw = db.execute(
        text("""
            SELECT start_date, end_date
            FROM employee_trainings
            WHERE id_no = :id_no AND start_date <= :ed AND end_date >= :sd
        """),
        {"id_no": id_no, "sd": sd, "ed": ed},
    ).fetchall()

    swipe_dates = {r[0] for r in swipes_raw}
    leave_ranges = [(r[0], r[1]) for r in leave_raw]
    training_ranges = [(r[0], r[1]) for r in training_raw]

    # User-configured holidays from rules_settings (only source)
    try:
        from owl.rules.engine import get_rule as _get_rule
        _holiday_dates = _get_rule("holidays", {}).get("dates", [])
    except Exception:
        _holiday_dates = []
    holiday_set: set[date] = set()
    for _d in _holiday_dates:
        try:
            holiday_set.add(date.fromisoformat(str(_d)))
        except ValueError:
            pass

    # Determine if employee is active (eligible to be absent) per configured eligible statuses
    from owl.rules.query_builder import get_active_statuses, get_working_weekdays
    from owl.rules.engine import get_rule
    emp_status_raw = str(emp[7] or "").strip().lower()
    active_statuses = {s.lower() for s in get_active_statuses()}
    is_active = emp_status_raw in active_statuses

    working_hours = get_rule("working_hours", {}) or {}
    incomplete_hours = (get_rule("incomplete_threshold", {"hours": 1}) or {}).get("hours", 1)
    working_dows = set(get_working_weekdays())
    leave_overrides_training = bool(get_rule("leave_overrides_training", True))

    swipe_map = {r[0]: r for r in swipes_raw}

    daily_attendance = []
    counts = {"present": 0, "absent": 0, "leave": 0, "training": 0}
    work_minutes = []
    current = sd
    while current <= ed:
        wd = current.weekday()
        status = _classify_day(current, leave_ranges, training_ranges, swipe_dates, holiday_set,
                               is_active, today, working_dows, leave_overrides_training)
        if status in counts:
            counts[status] += 1

        checkin_time = None
        checkout_time = None
        row = swipe_map.get(current)
        if row is not None:
            if row[1]:
                checkin_time = row[1].strftime("%H:%M")
            if row[2]:
                checkout_time = row[2].strftime("%H:%M")

        wh = working_hours.get(DAY_NAMES[wd]) if wd < 7 else None
        checkin_status = _classify_checkin(checkin_time, wh)
        checkout_status = _classify_checkout(checkin_time, checkout_time, wh, incomplete_hours)

        # Avg work hours: present days with both times, excluding leave/training
        if checkin_time and checkout_time and status not in ("leave", "training"):
            cim = _hm_to_min(checkin_time)
            com = _hm_to_min(checkout_time)
            if cim is not None and com is not None and com >= cim:
                work_minutes.append(com - cim)

        daily_attendance.append({
            "date": current.isoformat(),
            "status": status,
            "checkin_time": checkin_time,
            "checkout_time": checkout_time,
            "checkin_status": checkin_status,
            "checkout_status": checkout_status,
        })
        current += timedelta(days=1)

    avg_work_minutes = (sum(work_minutes) / len(work_minutes)) if work_minutes else None

    return {
        "employee": {
            "id_no": emp[0],
            "full_name": emp[1],
            "sex": emp[2],
            "geographical_zone": emp[3],
            "department": emp[4],
            "rank": emp[5],
            "grade_level": emp[6],
            "status": emp[7],
            "employment_type": emp[8],
            "phone_number": emp[9],
            "is_active": is_active,
        },
        "summary": counts,
        "avg_work_hours": _fmt_hours(avg_work_minutes),
        "daily_attendance": daily_attendance,
    }


@router.get("/employees/{id_no}/attendance-records")
def employee_attendance_records(
    id_no: str,
    start_date: str = Query(""),
    end_date: str = Query(""),
    type: str = Query("attendance", description="attendance | leave | training"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=0, le=1000),
    search: str = Query(""),
    sort_by: str = Query(""),
    sort_dir: str = Query("asc"),
    filters: str = Query(""),
    db: Session = Depends(get_db),
):
    try:
        parsed_filters = json.loads(filters) if filters else {}
    except Exception:
        parsed_filters = {}

    emp = db.execute(
        text("""
            SELECT e.id_no, e.status_id, es.status_name
            FROM employees e
            LEFT JOIN employee_statuses es ON e.status_id = es.status_id
            WHERE e.id_no = :id_no
        """),
        {"id_no": id_no},
    ).fetchone()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    today = date.today()
    if start_date and end_date:
        try:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")
        if sd > ed:
            raise HTTPException(status_code=422, detail="start_date must be <= end_date")
    else:
        sd = today.replace(day=1)
        ed = today

    from owl.rules.query_builder import get_active_statuses, get_working_weekdays
    from owl.rules.engine import get_rule
    is_active = str(emp[2] or "").strip().lower() in {s.lower() for s in get_active_statuses()}
    working_dows = set(get_working_weekdays())
    leave_overrides_training = bool(get_rule("leave_overrides_training", True))

    if type == "leave":
        rows_df = db.execute(
            text("""
                SELECT lr.start_date, COALESCE(lr.end_date, lr.start_date) AS end_date,
                       COALESCE(lt.leave_type_name, 'Unknown') AS leave_type
                FROM leave_records lr
                LEFT JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
                WHERE lr.id_no = :id_no AND lr.start_date <= :ed
                  AND COALESCE(lr.end_date, lr.start_date) >= :sd
                ORDER BY lr.start_date DESC
            """),
            {"id_no": id_no, "sd": sd, "ed": ed},
        ).fetchall()
        rows = []
        for r in rows_df:
            s, e = r[0], r[1]
            status = "Current" if (s and e and s <= today <= e) else "Taken"
            rows.append({
                "start_date": s.isoformat() if s else None,
                "end_date": e.isoformat() if e else None,
                "leave_type": r[2],
                "status": status,
            })
        columns = ["start_date", "end_date", "leave_type", "status"]
        numeric = []
        default_sort = "start_date"

    elif type == "training":
        rows_df = db.execute(
            text("""
                SELECT COALESCE(v.venue_name, 'Unknown') AS venue,
                       COALESCE(c.consultant_name, 'Unknown') AS consultant,
                       COALESCE(l.location_name, 'Unknown') AS location,
                       et.start_date, et.end_date, et.title
                FROM employee_trainings et
                LEFT JOIN venues v ON et.venue_id = v.venue_id
                LEFT JOIN consultants c ON et.consultant_id = c.consultant_id
                LEFT JOIN locations l ON et.location_id = l.location_id
                WHERE et.id_no = :id_no AND et.start_date <= :ed AND et.end_date >= :sd
                ORDER BY et.start_date DESC
            """),
            {"id_no": id_no, "sd": sd, "ed": ed},
        ).fetchall()
        rows = [
            {
                "venue": r[0], "consultant": r[1], "location": r[2],
                "start_date": r[3].isoformat() if r[3] else None,
                "end_date": r[4].isoformat() if r[4] else None,
                "title": r[5] or "",
            }
            for r in rows_df
        ]
        columns = ["venue", "consultant", "location", "start_date", "end_date", "title"]
        numeric = []
        default_sort = "start_date"

    else:
        # attendance — every weekday in range (weekends excluded)
        swipes_raw = db.execute(
            text("""
                SELECT DATE(swipe_time) AS swipe_date, MIN(swipe_time) AS checkin, MAX(swipe_time) AS checkout
                FROM employee_card_swipes
                WHERE id_no = :id_no AND swipe_time::date BETWEEN :sd AND :ed
                GROUP BY DATE(swipe_time)
            """),
            {"id_no": id_no, "sd": sd, "ed": ed},
        ).fetchall()
        swipe_dates = {r[0] for r in swipes_raw}
        swipe_map = {r[0]: r for r in swipes_raw}
        leave_raw = db.execute(
            text("""
                SELECT start_date, COALESCE(end_date, start_date) AS end_date
                FROM leave_records
                WHERE id_no = :id_no AND start_date <= :ed AND COALESCE(end_date, start_date) >= :sd
            """),
            {"id_no": id_no, "sd": sd, "ed": ed},
        ).fetchall()
        training_raw = db.execute(
            text("""
                SELECT start_date, end_date FROM employee_trainings
                WHERE id_no = :id_no AND start_date <= :ed AND end_date >= :sd
            """),
            {"id_no": id_no, "sd": sd, "ed": ed},
        ).fetchall()
        leave_ranges = [(r[0], r[1]) for r in leave_raw]
        training_ranges = [(r[0], r[1]) for r in training_raw]

        try:
            holiday_dates = get_rule("holidays", {}).get("dates", [])
        except Exception:
            holiday_dates = []
        holiday_set = set()
        for _d in holiday_dates:
            try:
                holiday_set.add(date.fromisoformat(str(_d)))
            except ValueError:
                pass

        working_hours = get_rule("working_hours", {}) or {}
        incomplete_hours = (get_rule("incomplete_threshold", {"hours": 1}) or {}).get("hours", 1)

        rows = []
        current = sd
        while current <= ed:
            if (current.weekday() + 1) in working_dows:  # configured working days only
                checkin_time = None
                checkout_time = None
                row = swipe_map.get(current)
                if row is not None:
                    if row[1]:
                        checkin_time = row[1].strftime("%H:%M")
                    if row[2]:
                        checkout_time = row[2].strftime("%H:%M")
                wh = working_hours.get(DAY_NAMES[current.weekday()])
                checkin_status = _classify_checkin(checkin_time, wh)
                checkout_status = _classify_checkout(checkin_time, checkout_time, wh, incomplete_hours)
                day_status = _classify_day(
                    current, leave_ranges, training_ranges, swipe_dates, holiday_set,
                    is_active, today, working_dows, leave_overrides_training
                )
                rows.append({
                    "day_date": f"{WEEKDAY_SHORT[current.weekday()]}, {current.day} {MONTH_SHORT[current.month - 1]} {current.year}",
                    "checkin_time": checkin_time or "",
                    "checkin_status": checkin_status or "",
                    "checkout_time": checkout_time or "",
                    "checkout_status": checkout_status or "",
                    "attendance_status": day_status.capitalize() if checkin_time else "",
                })
            current += timedelta(days=1)
        columns = ["day_date", "checkin_time", "checkin_status", "checkout_time", "checkout_status", "attendance_status"]
        numeric = []
        default_sort = "day_date"

    if not sort_by:
        sort_by = default_sort
    return _paginate_records(rows, columns, numeric, page, page_size, search, sort_by, sort_dir, parsed_filters)
