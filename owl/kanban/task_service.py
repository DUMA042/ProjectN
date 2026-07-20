"""
owl.kanban.task_service
~~~~~~~~~~~~~~~~~~~~~~~~
CRUD operations for Kanban tasks, with automatic history tracking on column moves.
"""

from datetime import datetime

from owl.load.database import get_session
from owl.load.models import KanbanTask, KanbanTaskAssignee, KanbanTaskHistory, KanbanColumn
from owl.logger import get_logger

log = get_logger(__name__)


def get_board_tasks(board_id: int) -> list[dict]:
    """Return all non-archived tasks on a board with assignees."""
    with get_session() as session:
        tasks = (
            session.query(KanbanTask)
            .filter(
                KanbanTask.board_id == board_id,
                KanbanTask.is_archived == False,
            )
            .order_by(KanbanTask.column_id, KanbanTask.position)
            .all()
        )
        task_ids = [t.task_id for t in tasks]
        assignees_by_task: dict[int, list] = {tid: [] for tid in task_ids}
        if task_ids:
            assigns = (
                session.query(KanbanTaskAssignee)
                .filter(KanbanTaskAssignee.task_id.in_(task_ids))
                .all()
            )
            for a in assigns:
                assignees_by_task[a.task_id].append(a)

        return _serialize_tasks(tasks, assignees_by_task)


def create_task(
    board_id: int, column_id: int, title: str,
    description: str | None = None, priority: str = "medium",
    due_date: str | None = None, assignee_id_nos: list[str] | None = None,
) -> dict:
    """Create a task and optionally assign staff."""
    with get_session() as session:
        task = KanbanTask(
            board_id=board_id,
            column_id=column_id,
            title=title,
            description=description,
            priority=priority,
            due_date=datetime.fromisoformat(due_date).date() if due_date else None,
        )
        session.add(task)
        session.flush()

        if assignee_id_nos:
            for id_no in assignee_id_nos:
                assignee = KanbanTaskAssignee(task_id=task.task_id, id_no=id_no)
                session.add(assignee)

        # First history entry — task was created into its initial column
        hist = KanbanTaskHistory(
            task_id=task.task_id,
            from_column_id=None,
            to_column_id=column_id,
        )
        session.add(hist)

        session.commit()
        log.info(f"Created task '{title}' (id={task.task_id}) on board {board_id}")
        return {"task_id": task.task_id, "title": task.title}


def move_task(task_id: int, to_column_id: int, moved_by: str | None = None) -> dict:
    """Move a task to a new column. Auto-calculates duration_in_previous and writes history."""
    with get_session() as session:
        task = session.query(KanbanTask).filter(KanbanTask.task_id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        from_column_id = task.column_id
        now = datetime.now()

        # Calculate duration_in_previous
        last_history = (
            session.query(KanbanTaskHistory)
            .filter(KanbanTaskHistory.task_id == task_id)
            .order_by(KanbanTaskHistory.moved_at.desc())
            .first()
        )
        duration = now - last_history.moved_at if last_history else None

        # Update task location
        task.column_id = to_column_id
        task.updated_at = now

        # Check if destination column is a done column
        dest_column = session.query(KanbanColumn).filter(KanbanColumn.column_id == to_column_id).first()
        if dest_column and dest_column.is_done_column:
            task.completed_at = now

        # Write movement history
        hist = KanbanTaskHistory(
            task_id=task_id,
            from_column_id=from_column_id,
            to_column_id=to_column_id,
            moved_by=moved_by,
            moved_at=now,
            duration_in_previous=duration,
        )
        session.add(hist)
        session.commit()

        log.info(f"Moved task {task_id} from column {from_column_id} to {to_column_id}")
        return {
            "task_id": task_id,
            "from_column_id": from_column_id,
            "to_column_id": to_column_id,
            "duration_seconds": duration.total_seconds() if duration else None,
        }


def assign_task(task_id: int, id_no: str, assigned_by: str | None = None) -> dict:
    """Assign a staff member to a task."""
    with get_session() as session:
        assignee = KanbanTaskAssignee(task_id=task_id, id_no=id_no, assigned_by=assigned_by)
        session.add(assignee)
        session.commit()
        return {"assignment_id": assignee.assignment_id, "task_id": task_id, "id_no": id_no}


def get_task_history(task_id: int) -> list[dict]:
    """Return the full movement history of a task."""
    with get_session() as session:
        rows = (
            session.query(KanbanTaskHistory)
            .filter(KanbanTaskHistory.task_id == task_id)
            .order_by(KanbanTaskHistory.moved_at.asc())
            .all()
        )
        return [
            {
                "history_id": h.history_id,
                "from_column_id": h.from_column_id,
                "to_column_id": h.to_column_id,
                "moved_by": h.moved_by,
                "moved_at": h.moved_at.isoformat(),
                "duration_in_previous": str(h.duration_in_previous) if h.duration_in_previous else None,
            }
            for h in rows
        ]


def _serialize_tasks(tasks, assignees_by_task: dict) -> list[dict]:
    return [
        {
            "task_id": t.task_id,
            "board_id": t.board_id,
            "column_id": t.column_id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "position": t.position,
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "assignees": [
                {"assignment_id": a.assignment_id, "id_no": a.id_no}
                for a in assignees_by_task.get(t.task_id, [])
            ],
        }
        for t in tasks
    ]
