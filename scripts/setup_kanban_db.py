"""
scripts/setup_kanban_db.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Creates the 7 Kanban board tables in the existing flowdb database.

Tables Created
--------------
1. kanban_boards         — Top-level project/initiative containers
2. kanban_columns        — Flexible stages within a board
3. kanban_labels         — Reusable tags for tasks
4. kanban_tasks          — The actual task cards
5. kanban_task_assignees — Links tasks to staff (employees.id_no)
6. kanban_task_labels    — Many-to-many junction for task tags
7. kanban_task_history   — Full movement audit log with duration tracking

Usage
-----
    python scripts/setup_kanban_db.py
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"


DDL = """
-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. KANBAN BOARDS
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_boards (
    board_id        SERIAL          PRIMARY KEY,
    board_name      VARCHAR(255)    NOT NULL UNIQUE,
    description     TEXT,
    department_id   INTEGER         REFERENCES departments(department_id) ON DELETE SET NULL,
    is_archived     BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE kanban_boards IS 'Top-level Kanban board container. Each board represents a project, initiative, or department workflow.';


-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. KANBAN COLUMNS
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_columns (
    column_id       SERIAL          PRIMARY KEY,
    board_id        INTEGER         NOT NULL REFERENCES kanban_boards(board_id) ON DELETE CASCADE,
    column_name     VARCHAR(255)    NOT NULL,
    position        INTEGER         NOT NULL DEFAULT 0,
    color           VARCHAR(7),
    is_done_column  BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE(board_id, column_name)
);

COMMENT ON TABLE kanban_columns IS 'Flexible stages within a board. Unlimited columns per board, ordered by position.';


-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. KANBAN LABELS
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_labels (
    label_id        SERIAL          PRIMARY KEY,
    label_name      VARCHAR(100)    NOT NULL UNIQUE,
    color           VARCHAR(7)
);

COMMENT ON TABLE kanban_labels IS 'Reusable tags/labels that can be applied to tasks across any board.';


-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. KANBAN TASKS
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_tasks (
    task_id         SERIAL          PRIMARY KEY,
    board_id        INTEGER         NOT NULL REFERENCES kanban_boards(board_id) ON DELETE CASCADE,
    column_id       INTEGER         NOT NULL REFERENCES kanban_columns(column_id),
    title           VARCHAR(500)    NOT NULL,
    description     TEXT,
    priority        VARCHAR(20)     NOT NULL DEFAULT 'medium',
    due_date        DATE,
    position        INTEGER         NOT NULL DEFAULT 0,
    is_archived     BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,

    CONSTRAINT chk_priority CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

COMMENT ON TABLE kanban_tasks IS 'The actual task/card. Core entity of the Kanban system.';


-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. KANBAN TASK ASSIGNEES
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_task_assignees (
    assignment_id   SERIAL          PRIMARY KEY,
    task_id         INTEGER         NOT NULL REFERENCES kanban_tasks(task_id) ON DELETE CASCADE,
    id_no           VARCHAR(64)     REFERENCES employees(id_no) ON DELETE SET NULL,
    assigned_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    assigned_by     VARCHAR(64),

    UNIQUE(task_id, id_no)
);

COMMENT ON TABLE kanban_task_assignees IS 'Many-to-many junction linking tasks to staff. Zero assignees = unassigned company goal.';


-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. KANBAN TASK LABELS
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_task_labels (
    task_id         INTEGER         NOT NULL REFERENCES kanban_tasks(task_id) ON DELETE CASCADE,
    label_id        INTEGER         NOT NULL REFERENCES kanban_labels(label_id) ON DELETE CASCADE,

    PRIMARY KEY (task_id, label_id)
);

COMMENT ON TABLE kanban_task_labels IS 'Many-to-many junction linking tasks to labels/tags.';


-- ═══════════════════════════════════════════════════════════════════════════════
-- 7. KANBAN TASK HISTORY (Movement Tracker)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS kanban_task_history (
    history_id              SERIAL          PRIMARY KEY,
    task_id                 INTEGER         NOT NULL REFERENCES kanban_tasks(task_id) ON DELETE CASCADE,
    from_column_id          INTEGER         REFERENCES kanban_columns(column_id),
    to_column_id            INTEGER         NOT NULL REFERENCES kanban_columns(column_id),
    moved_by                VARCHAR(64),
    moved_at                TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    duration_in_previous    INTERVAL
);

COMMENT ON TABLE kanban_task_history IS 'Audit log of every task movement between columns. duration_in_previous tracks time spent in the previous column.';

-- Index for fast history lookups by task
CREATE INDEX IF NOT EXISTS idx_kanban_task_history_task_id
    ON kanban_task_history(task_id);

-- Index for fast lookups of tasks by board and column
CREATE INDEX IF NOT EXISTS idx_kanban_tasks_board_column
    ON kanban_tasks(board_id, column_id);

-- Index for fast assignee lookups by staff
CREATE INDEX IF NOT EXISTS idx_kanban_task_assignees_id_no
    ON kanban_task_assignees(id_no);
"""


def main():
    print("Connecting to flowdb...")
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("Creating Kanban tables...")
        cur.execute(DDL)
        print("All 7 Kanban tables created successfully!")

        # Verify
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE 'kanban_%'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print(f"\nVerification — {len(tables)} Kanban table(s) found:")
        for t in tables:
            print(f"  - {t[0]}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
