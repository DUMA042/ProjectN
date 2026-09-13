"""Staff endpoints — paginated directory + employee profile + attendance stats."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.dependencies import get_db

router = APIRouter(tags=["staff"])


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
    from owl.rules.query_builder import get_active_statuses
    emp_status_raw = str(emp[7] or "").strip().lower()
    active_statuses = {s.lower() for s in get_active_statuses()}
    is_active = emp_status_raw in active_statuses

    daily_attendance = []
    counts = {"present": 0, "absent": 0, "leave": 0, "training": 0}
    current = sd
    while current <= ed:
        wd = current.weekday()
        # Weekend always wins → holiday on weekend is ignored
        if wd >= 5:
            daily_attendance.append({
                "date": current.isoformat(),
                "status": "weekend",
                "checkin_time": None,
                "checkout_time": None,
            })
            current += timedelta(days=1)
            continue
        if current in holiday_set:
            daily_attendance.append({
                "date": current.isoformat(),
                "status": "holiday",
                "checkin_time": None,
                "checkout_time": None,
            })
            current += timedelta(days=1)
            continue
        status = None
        for ls, le in leave_ranges:
            if ls <= current <= le:
                status = "leave"
                break
        if not status:
            for ts, te in training_ranges:
                if ts <= current <= te:
                    status = "training"
                    break
        if not status and current in swipe_dates:
            status = "present"
        if not status:
            if not is_active:
                status = "inactive"
            elif current >= today:
                status = "upcoming"
            else:
                status = "absent"
        if status in counts:
            counts[status] += 1

        checkin_time = None
        checkout_time = None
        for r in swipes_raw:
            if r[0] == current:
                if r[1]:
                    checkin_time = r[1].strftime("%H:%M")
                if r[2]:
                    checkout_time = r[2].strftime("%H:%M")
                break

        daily_attendance.append({
            "date": current.isoformat(),
            "status": status,
            "checkin_time": checkin_time,
            "checkout_time": checkout_time,
        })
        current += timedelta(days=1)

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
        },
        "summary": counts,
        "daily_attendance": daily_attendance,
    }
