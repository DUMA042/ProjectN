"""Privacy token vault — reversible anonymization for shared/CSV exports.

Names/IDs map to random 32-hex tokens persisted in ``privacy_tokens`` (stable
reuse, unhashable weeks later across restarts). Names-only, IDs-only, or both
is expressed by which lists the caller fills. Blanks pass through untouched.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from owl.load.database import get_session
from owl.privacy.vault import forget_tokens, get_or_create_tokens, resolve_tokens

router = APIRouter(tags=["privacy"])


class TokenizeRequest(BaseModel):
    names: list[str] = []
    ids: list[str] = []


class UnhashRequest(BaseModel):
    tokens: list[str] = []


class ForgetRequest(BaseModel):
    tokens: list[str] = []


@router.post("/privacy/tokenize")
def privacy_tokenize(body: TokenizeRequest):
    try:
        with get_session() as s:
            return {
                "names": get_or_create_tokens(s, "name", body.names),
                "ids": get_or_create_tokens(s, "id", body.ids),
            }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/privacy/unhash")
def privacy_unhash(body: UnhashRequest):
    try:
        with get_session() as s:
            return {"tokens": resolve_tokens(s, body.tokens)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/privacy/forget")
def privacy_forget(body: ForgetRequest):
    try:
        with get_session() as s:
            return {"forgotten": forget_tokens(s, body.tokens)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
