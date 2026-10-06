"""Assistant chat proxy — the ONLY place the DeepSeek key is ever used.

The key travels from the operator's local .env into the outbound Authorization
header and nowhere else: it is never logged, never sent to the frontend, and
no endpoint returns it (health reports a boolean only).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from owl.ai import deepseek
from owl.ai.context import SYSTEM_PREAMBLE, schema_summary
from owl.config import settings
from owl.load.database import get_session

router = APIRouter(tags=["assistant"])

MAX_MESSAGES = 20
MAX_CONTENT_CHARS = 2000


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.get("/assistant/health")
def assistant_health():
    return {
        "configured": bool(settings.deepseek_api_key.strip()),
        "model": settings.deepseek_model.strip() or "deepseek-chat",
    }


@router.post("/assistant/chat")
def assistant_chat(body: ChatRequest):
    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    if len(body.messages) > MAX_MESSAGES:
        raise HTTPException(status_code=400, detail="Too many messages in one request")
    clean: list[dict[str, str]] = []
    for m in body.messages:
        role = m.role.strip().lower()
        if role not in ("user", "assistant"):
            raise HTTPException(status_code=400, detail="Roles must be 'user' or 'assistant'")
        content = m.content.strip()
        if not content:
            continue
        clean.append({"role": role, "content": content[:MAX_CONTENT_CHARS]})
    if not any(m["role"] == "user" for m in clean):
        raise HTTPException(status_code=400, detail="Nothing to send")

    try:
        with get_session() as s:
            system = f"{SYSTEM_PREAMBLE}\n{schema_summary(s)}"
    except Exception:
        system = SYSTEM_PREAMBLE

    try:
        reply = deepseek.chat(clean, system=system)
    except deepseek.NotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except deepseek.DeepSeekError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"reply": reply}
