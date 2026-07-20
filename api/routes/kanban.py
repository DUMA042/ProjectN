"""Kanban endpoints — CRUD for boards, columns, tasks, labels, assignees, history."""

from fastapi import APIRouter, HTTPException, Query

from owl.kanban import board_service, task_service, label_service

router = APIRouter(tags=["kanban"])


# ── Boards ──────────────────────────────────────────────────────────────────────

@router.get("/kanban/boards")
def kanban_boards():
    return board_service.get_boards()


@router.post("/kanban/boards")
def kanban_create_board(
    name: str, description: str | None = None, columns: str | None = None
):
    col_list = [c.strip() for c in columns.split(",")] if columns else None
    return board_service.create_board(name, description, col_list)


@router.post("/kanban/boards/{board_id}/columns")
def kanban_add_column(
    board_id: int, column_name: str, position: int | None = None, color: str | None = None
):
    return board_service.add_column(board_id, column_name, position, color)


# ── Tasks ───────────────────────────────────────────────────────────────────────

@router.get("/kanban/boards/{board_id}/tasks")
def kanban_board_tasks(board_id: int):
    return task_service.get_board_tasks(board_id)


@router.post("/kanban/tasks")
def kanban_create_task(
    board_id: int, column_id: int, title: str,
    description: str | None = None, priority: str = "medium",
    due_date: str | None = None, assignee_ids: str | None = None,
):
    assignee_list = (
        [a.strip() for a in assignee_ids.split(",")] if assignee_ids else None
    )
    return task_service.create_task(
        board_id, column_id, title, description, priority, due_date, assignee_list,
    )


@router.patch("/kanban/tasks/{task_id}/move")
def kanban_move_task(task_id: int, to_column_id: int, moved_by: str | None = None):
    return task_service.move_task(task_id, to_column_id, moved_by)


@router.post("/kanban/tasks/{task_id}/assign")
def kanban_assign_task(task_id: int, id_no: str, assigned_by: str | None = None):
    return task_service.assign_task(task_id, id_no, assigned_by)


@router.get("/kanban/tasks/{task_id}/history")
def kanban_task_history(task_id: int):
    return task_service.get_task_history(task_id)


# ── Labels ──────────────────────────────────────────────────────────────────────

@router.get("/kanban/labels")
def kanban_labels():
    return label_service.get_labels()


@router.post("/kanban/labels")
def kanban_create_label(name: str, color: str | None = None):
    return label_service.create_label(name, color)
