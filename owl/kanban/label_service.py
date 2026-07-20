"""
owl.kanban.label_service
~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD operations for Kanban labels.
"""

from owl.load.database import get_session
from owl.load.models import KanbanLabel
from owl.logger import get_logger

log = get_logger(__name__)


def get_labels() -> list[dict]:
    """Return all labels."""
    with get_session() as session:
        labels = session.query(KanbanLabel).order_by(KanbanLabel.label_name).all()
        return [
            {"label_id": l.label_id, "label_name": l.label_name, "color": l.color}
            for l in labels
        ]


def create_label(name: str, color: str | None = None) -> dict:
    """Create a new label."""
    with get_session() as session:
        label = KanbanLabel(label_name=name, color=color)
        session.add(label)
        session.commit()
        log.info(f"Created label '{name}' (id={label.label_id})")
        return {"label_id": label.label_id, "label_name": label.label_name}
