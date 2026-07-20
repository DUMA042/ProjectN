"""
owl.kanban.board_service
~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD operations for Kanban boards and columns.
"""

from owl.load.database import get_session
from owl.load.models import KanbanBoard, KanbanColumn
from owl.logger import get_logger

log = get_logger(__name__)


def get_boards() -> list[dict]:
    """Return all non-archived boards with their columns."""
    with get_session() as session:
        boards = (
            session.query(KanbanBoard)
            .filter(KanbanBoard.is_archived == False)
            .order_by(KanbanBoard.created_at.desc())
            .all()
        )
        board_ids = [b.board_id for b in boards]
        columns_by_board: dict[int, list] = {bid: [] for bid in board_ids}
        if board_ids:
            cols = (
                session.query(KanbanColumn)
                .filter(KanbanColumn.board_id.in_(board_ids))
                .order_by(KanbanColumn.position)
                .all()
            )
            for c in cols:
                columns_by_board[c.board_id].append(c)

        return [
            {
                "board_id": b.board_id,
                "board_name": b.board_name,
                "description": b.description,
                "department_id": b.department_id,
                "created_at": b.created_at.isoformat(),
                "columns": [
                    {
                        "column_id": c.column_id,
                        "column_name": c.column_name,
                        "position": c.position,
                        "color": c.color,
                        "is_done_column": c.is_done_column,
                    }
                    for c in columns_by_board.get(b.board_id, [])
                ],
            }
            for b in boards
        ]


def create_board(name: str, description: str | None = None, columns: list[str] | None = None) -> dict:
    """Create a new board with optional default columns."""
    with get_session() as session:
        board = KanbanBoard(board_name=name, description=description)
        session.add(board)
        session.flush()

        if columns:
            for i, col_name in enumerate(columns):
                col = KanbanColumn(
                    board_id=board.board_id,
                    column_name=col_name,
                    position=i,
                )
                session.add(col)

        session.commit()
        log.info(f"Created board '{name}' (id={board.board_id}) with {len(columns or [])} columns")
        return {"board_id": board.board_id, "board_name": board.board_name}


def add_column(board_id: int, column_name: str, position: int | None = None, color: str | None = None) -> dict:
    """Add a column to an existing board."""
    with get_session() as session:
        col = KanbanColumn(
            board_id=board_id,
            column_name=column_name,
            position=position or 0,
            color=color,
        )
        session.add(col)
        session.commit()
        return {"column_id": col.column_id, "column_name": col.column_name}
