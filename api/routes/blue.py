"""BLUE Q&A — general-purpose read-only query pipeline (no input redaction).

USER -> AI(IR) -> validate -> policy -> compile -> security-validate ->
read-only execute -> result contract -> optional narration -> UI.

The user message reaches the model verbatim. The model never receives
credentials, connections, tools, row data, or token maps. Responses carry
real values for UI display only (same trust boundary as every other endpoint
in this app).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from owl.ai import pipeline
from owl.load.database import get_session

router = APIRouter(tags=["blue"])


class BlueAskRequest(BaseModel):
    question: str = ""


@router.post("/blue/ask")
def blue_ask(body: BlueAskRequest):
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="No question provided")
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question too long (max 2000 characters)")
    with get_session() as s:
        try:
            result = pipeline.run_ask(s, question)
        except Exception:
            raise HTTPException(status_code=500, detail="Could not process that question. Please try again.")
    return {
        "answer": result["answer"],
        "rows": result.get("rows", []),
        "columns": result.get("columns", []),
        "row_count": result.get("row_count", 0),
        "truncated": result.get("truncated", False),
        "mode": result.get("mode", "unsupported"),
        "sql": result.get("sql"),
    }
