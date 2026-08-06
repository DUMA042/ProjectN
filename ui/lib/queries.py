from ui.lib.db import run_query


def get_dashboard_summary():
    return run_query("""
        SELECT
            (SELECT COUNT(*) FROM employees) AS total_employees,
            (SELECT COUNT(*) FROM employees e
             JOIN employee_statuses s ON e.status_id = s.status_id
             WHERE LOWER(s.status_name) = 'active') AS active_employees,
            (SELECT COUNT(DISTINCT lr.id_no) FROM leave_records lr
             WHERE CURRENT_DATE BETWEEN lr.start_date AND COALESCE(lr.end_date, lr.start_date)) AS staff_on_leave,
            (SELECT COUNT(DISTINCT et.id_no) FROM employee_trainings et
             WHERE CURRENT_DATE BETWEEN et.start_date AND et.end_date) AS staff_in_training
    """)


def get_department_distribution():
    return run_query("""
        SELECT
            COALESCE(d.department_name, 'Unknown') AS department_name,
            COUNT(e.id_no) AS employee_count
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        GROUP BY d.department_name
        ORDER BY employee_count DESC
    """)


def get_status_distribution():
    return run_query("""
        SELECT
            es.status_name,
            COUNT(e.id_no) AS employee_count
        FROM employees e
        JOIN employee_statuses es ON e.status_id = es.status_id
        GROUP BY es.status_name
        ORDER BY employee_count DESC
    """)


def get_leave_breakdown_by_type():
    return run_query("""
        SELECT
            lt.leave_type_name,
            COUNT(lr.record_id) AS total_entries,
            COUNT(DISTINCT lr.id_no) AS unique_staff
        FROM leave_records lr
        JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
        GROUP BY lt.leave_type_name
        ORDER BY total_entries DESC
    """)


def get_recent_ingestions(limit=20):
    return run_query("""
        SELECT
            id::TEXT,
            original_filename,
            normalized_filename,
            report_type,
            status,
            error_context,
            created_at,
            processed_at
        FROM file_ingestion_meta
        ORDER BY created_at DESC
        LIMIT :limit
    """, {"limit": limit})


def get_card_swipe_summary(today_only: bool = False):
    where = "WHERE swipe_time::date = CURRENT_DATE" if today_only else ""
    return run_query(f"""
        SELECT
            COUNT(*) AS total_swipes,
            COUNT(DISTINCT id_no) AS unique_employees,
            MIN(swipe_time) AS first_swipe,
            MAX(swipe_time) AS last_swipe
        FROM employee_card_swipes
        {where}
    """)


def get_card_swipe_by_day(days=30):
    return run_query(f"""
        SELECT
            DATE(swipe_time) AS swipe_date,
            COUNT(*) AS swipe_count
        FROM employee_card_swipes
        WHERE swipe_time >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY DATE(swipe_time)
        ORDER BY swipe_date
    """)


def get_card_swipe_by_hour():
    return run_query("""
        SELECT
            EXTRACT(HOUR FROM swipe_time)::INT AS hour,
            COUNT(*) AS swipe_count
        FROM employee_card_swipes
        GROUP BY hour
        ORDER BY hour
    """)


def get_card_swipe_by_location():
    return run_query("""
        SELECT
            COALESCE(l.location_name, 'Unknown') AS location_name,
            COUNT(*) AS swipe_count
        FROM employee_card_swipes cs
        LEFT JOIN locations l ON cs.location_id = l.location_id
        GROUP BY l.location_name
        ORDER BY swipe_count DESC
    """)


def get_card_swipe_by_month():
    return run_query("""
        SELECT
            TO_CHAR(swipe_time, 'YYYY-MM') AS month,
            COUNT(*) AS swipe_count
        FROM employee_card_swipes
        GROUP BY month
        ORDER BY month
    """)


def get_recent_card_swipes(limit=50):
    return run_query("""
        SELECT
            cs.swipe_id,
            cs.id_no,
            e.full_name,
            cs.swipe_time,
            COALESCE(l.location_name, 'Unknown') AS location
        FROM employee_card_swipes cs
        LEFT JOIN employees e ON cs.id_no = e.id_no
        LEFT JOIN locations l ON cs.location_id = l.location_id
        ORDER BY cs.swipe_time DESC
        LIMIT :limit
    """, {"limit": limit})


def get_leave_summary():
    return run_query("""
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT id_no) AS unique_staff,
            COUNT(DISTINCT leave_type_id) AS leave_types_used
        FROM leave_records
    """)


def get_leave_by_month():
    return run_query("""
        SELECT
            TO_CHAR(start_date, 'YYYY-MM') AS month,
            COUNT(*) AS record_count
        FROM leave_records
        WHERE start_date IS NOT NULL
        GROUP BY month
        ORDER BY month
    """)


def get_recent_leaves(limit=50):
    return run_query("""
        SELECT
            lr.record_id,
            lr.id_no,
            e.full_name,
            lt.leave_type_name,
            lr.start_date,
            lr.end_date
        FROM leave_records lr
        LEFT JOIN employees e ON lr.id_no = e.id_no
        LEFT JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
        ORDER BY lr.start_date DESC
        LIMIT :limit
    """, {"limit": limit})


def get_training_summary():
    return run_query("""
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT id_no) AS unique_staff,
            COUNT(DISTINCT venue_id) AS venues_used,
            COUNT(DISTINCT consultant_id) AS consultants_used
        FROM employee_trainings
    """)


def get_training_by_venue():
    return run_query("""
        SELECT
            COALESCE(v.venue_name, 'Unknown') AS venue_name,
            COUNT(*) AS record_count
        FROM employee_trainings et
        LEFT JOIN venues v ON et.venue_id = v.venue_id
        GROUP BY v.venue_name
        ORDER BY record_count DESC
    """)


def get_training_by_consultant():
    return run_query("""
        SELECT
            COALESCE(c.consultant_name, 'Unknown') AS consultant_name,
            COUNT(*) AS record_count
        FROM employee_trainings et
        LEFT JOIN consultants c ON et.consultant_id = c.consultant_id
        GROUP BY c.consultant_name
        ORDER BY record_count DESC
    """)


def get_recent_trainings(limit=50):
    return run_query("""
        SELECT
            et.training_id,
            et.id_no,
            e.full_name,
            COALESCE(v.venue_name, 'Unknown') AS venue,
            COALESCE(c.consultant_name, 'Unknown') AS consultant,
            et.start_date,
            et.end_date,
            et.title
        FROM employee_trainings et
        LEFT JOIN employees e ON et.id_no = e.id_no
        LEFT JOIN venues v ON et.venue_id = v.venue_id
        LEFT JOIN consultants c ON et.consultant_id = c.consultant_id
        ORDER BY et.start_date DESC
        LIMIT :limit
    """, {"limit": limit})


def search_employees(search="", department="", status="", page=1, size=50):
    where = []
    params = {"offset": (page - 1) * size, "limit": size}

    if search:
        where.append("(LOWER(e.full_name) LIKE :search OR LOWER(e.id_no) LIKE :search)")
        params["search"] = f"%{search.lower()}%"
    if department:
        where.append("LOWER(d.department_name) = :dept")
        params["dept"] = department.lower()
    if status:
        where.append("LOWER(s.status_name) = :status")
        params["status"] = status.lower()

    where_sql = " AND ".join(where) if where else "TRUE"

    sql = f"""
        SELECT e.id_no, e.full_name, e.sex,
               d.department_name, r.rank_name, gl.gl_name,
               s.status_name, e.geographical_zone,
               e.date_of_last_deployment, e.remark, e.phone_number
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN ranks r ON e.rank_id = r.rank_id
        LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
        LEFT JOIN employee_statuses s ON e.status_id = s.status_id
        WHERE {where_sql}
        ORDER BY e.full_name
        LIMIT :limit OFFSET :offset
    """
    count_sql = f"SELECT COUNT(*) FROM employees e WHERE {where_sql}"

    df = run_query(sql, params)
    count_params = {k: v for k, v in params.items() if k not in ("offset", "limit")}
    total = run_query(count_sql, count_params).iloc[0, 0] if not run_query(count_sql, count_params).empty else 0

    return df, int(total)


def get_departments():
    return run_query("""
        SELECT DISTINCT d.department_name
        FROM departments d
        JOIN employees e ON e.department_id = d.department_id
        ORDER BY d.department_name
    """)["department_name"].tolist()


def get_statuses():
    return run_query("""
        SELECT DISTINCT s.status_name
        FROM employee_statuses s
        ORDER BY s.status_name
    """)["status_name"].tolist()


# ── Dashboard Custom Queries ──────────────────────────────────────────────────

def get_workforce_status(start_date: str, end_date: str, department: str = ""):
    dept_filter = ""
    params = {"start_date": start_date, "end_date": end_date}
    if department:
        dept_filter = "AND d.department_name = :department"
        params["department"] = department
    return run_query(f"""
        WITH base_active AS (
            SELECT e.id_no, d.department_name
            FROM employees e
            JOIN employee_statuses es ON e.status_id = es.status_id
            JOIN locations l ON e.location_id = l.location_id
            JOIN departments d ON e.department_id = d.department_id
            WHERE LOWER(es.status_name) = 'active'
              AND LOWER(l.location_name) = 'hq'
              {dept_filter}
        ),
        on_leave_range AS (
            SELECT DISTINCT id_no
            FROM leave_records
            WHERE start_date <= :end_date
              AND COALESCE(end_date, start_date) >= :start_date
        ),
        on_training_range AS (
            SELECT DISTINCT id_no
            FROM employee_trainings
            WHERE start_date <= :end_date
              AND end_date >= :start_date
        ),
        classified AS (
            SELECT
                CASE
                    WHEN ol.id_no IS NOT NULL THEN 'On Leave'
                    WHEN ot.id_no IS NOT NULL THEN 'On Training'
                    ELSE 'Active (Available)'
                END AS status_category
            FROM base_active b
            LEFT JOIN on_leave_range ol ON ol.id_no = b.id_no
            LEFT JOIN on_training_range ot ON ot.id_no = b.id_no
        )
        SELECT
            status_category AS status,
            COUNT(*)::int AS count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM classified
        GROUP BY status_category
        ORDER BY
            CASE status_category
                WHEN 'On Leave' THEN 1
                WHEN 'On Training' THEN 2
                WHEN 'Active (Available)' THEN 3
            END
    """, params)


def get_dept_attendance(start_date: str, end_date: str, department: str = ""):
    dept_filter = ""
    params = {"start_date": start_date, "end_date": end_date}
    if department:
        dept_filter = "AND d.department_name = :department"
        params["department"] = department
    return run_query(f"""
        WITH base_active AS (
            SELECT e.id_no, d.department_name
            FROM employees e
            JOIN employee_statuses es ON e.status_id = es.status_id
            JOIN locations l ON e.location_id = l.location_id
            JOIN departments d ON e.department_id = d.department_id
            WHERE LOWER(es.status_name) = 'active'
              AND LOWER(l.location_name) = 'hq'
              {dept_filter}
        ),
        swiped_in_range AS (
            SELECT DISTINCT id_no FROM employee_card_swipes
            WHERE swipe_time::date BETWEEN :start_date AND :end_date
        ),
        on_leave_range AS (
            SELECT DISTINCT id_no FROM leave_records
            WHERE start_date <= :end_date
              AND COALESCE(end_date, start_date) >= :start_date
        ),
        on_training_range AS (
            SELECT DISTINCT id_no FROM employee_trainings
            WHERE start_date <= :end_date
              AND end_date >= :start_date
        ),
        classified AS (
            SELECT
                b.department_name,
                CASE
                    WHEN ol.id_no IS NOT NULL THEN 'Leave'
                    WHEN ot.id_no IS NOT NULL THEN 'Training'
                    WHEN sw.id_no IS NOT NULL THEN 'Attendance'
                    ELSE 'Absent'
                END AS status_category
            FROM base_active b
            LEFT JOIN swiped_in_range sw ON sw.id_no = b.id_no
            LEFT JOIN on_leave_range ol ON ol.id_no = b.id_no
            LEFT JOIN on_training_range ot ON ot.id_no = b.id_no
        ),
        dept_counts AS (
            SELECT
                department_name,
                COUNT(*) FILTER (WHERE status_category = 'Attendance') AS attendance_count,
                COUNT(*) FILTER (WHERE status_category = 'Absent') AS absent_count,
                COUNT(*) FILTER (WHERE status_category = 'Leave') AS leave_count,
                COUNT(*) FILTER (WHERE status_category = 'Training') AS training_count,
                COUNT(*) AS total_staff
            FROM classified
            GROUP BY department_name
        )
        SELECT
            department_name,
            attendance_count,
            ROUND(100.0 * attendance_count / NULLIF(total_staff, 0), 2) AS attendance_pct,
            absent_count,
            ROUND(100.0 * absent_count / NULLIF(total_staff, 0), 2) AS absent_pct,
            leave_count,
            ROUND(100.0 * leave_count / NULLIF(total_staff, 0), 2) AS leave_pct,
            training_count,
            ROUND(100.0 * training_count / NULLIF(total_staff, 0), 2) AS training_pct,
            total_staff
        FROM dept_counts
        ORDER BY department_name
    """, params)


def get_earliest_checkins(start_date: str, end_date: str, limit: int = 10):
    single_day = start_date == end_date
    if single_day:
        return run_query("""
            SELECT DISTINCT ON (cs.id_no)
                cs.id_no,
                e.full_name,
                COALESCE(d.department_name, 'Unknown') AS department,
                TO_CHAR(MIN(cs.swipe_time) OVER (PARTITION BY cs.id_no), 'HH24:MI') AS swipe_time
            FROM employee_card_swipes cs
            JOIN employees e ON cs.id_no = e.id_no
            LEFT JOIN departments d ON e.department_id = d.department_id
            WHERE cs.swipe_time::date = :start_date
            ORDER BY cs.id_no, swipe_time ASC
            LIMIT :limit
        """, {"start_date": start_date, "limit": limit})
    else:
        return run_query("""
            SELECT
                cs.id_no,
                e.full_name,
                COALESCE(d.department_name, 'Unknown') AS department,
                TO_CHAR((AVG(EXTRACT(EPOCH FROM cs.swipe_time::time)) * INTERVAL '1 second')::time, 'HH24:MI') AS swipe_time
            FROM employee_card_swipes cs
            JOIN employees e ON cs.id_no = e.id_no
            LEFT JOIN departments d ON e.department_id = d.department_id
            WHERE cs.swipe_time::date BETWEEN :start_date AND :end_date
            GROUP BY cs.id_no, e.full_name, d.department_name
            ORDER BY AVG(EXTRACT(EPOCH FROM cs.swipe_time::time))
            LIMIT :limit
        """, {"start_date": start_date, "end_date": end_date, "limit": limit})


def get_employee_summary():
    return run_query("""
        SELECT
            e.id_no,
            e.full_name,
            COALESCE(d.department_name, 'Unknown') AS department,
            COALESCE(gl.gl_name, 'Unknown') AS grade_level,
            COUNT(DISTINCT cs.swipe_time::date) AS days_present,
            COUNT(DISTINCT lr.record_id) AS leave_records_count,
            COUNT(DISTINCT et.training_id) AS training_records_count
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
        LEFT JOIN employee_card_swipes cs ON cs.id_no = e.id_no
        LEFT JOIN leave_records lr ON lr.id_no = e.id_no
        LEFT JOIN employee_trainings et ON et.id_no = e.id_no
        WHERE e.status_id IN (SELECT status_id FROM employee_statuses WHERE LOWER(status_name) = 'active')
        GROUP BY e.id_no, e.full_name, d.department_name, gl.gl_name
        ORDER BY e.full_name
        LIMIT 200
    """)
