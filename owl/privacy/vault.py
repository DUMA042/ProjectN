"""Reversible token vault (hashprocessor model, hardened).

Each sensitive value maps to a cryptographically random 32-char hex token,
persisted in the ``privacy_tokens`` table so any hashed file can be unhashed
weeks later, across restarts. Lookup keys are normalized (strip / collapse /
casefold) so one person always reuses one token; the first-seen display form
is kept for human-readable unhash. Blanks are never tokenized.
"""
from __future__ import annotations

import secrets

from sqlalchemy import text
from sqlalchemy.orm import Session

KINDS = ("name", "id")
MAX_VALUES = 5000
TOKEN_BYTES = 16


def normalize(value: object) -> str:
    """Lookup key: strip, collapse inner whitespace, casefold."""
    return " ".join(str(value).split()).casefold()


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"Unknown token kind '{kind}' (expected one of {KINDS})")


def _check_values(values: list) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("values must be a list of strings")
    if len(values) > MAX_VALUES:
        raise ValueError(f"Too many values (max {MAX_VALUES})")
    return ["" if v is None else str(v) for v in values]


def _mint_token(session: Session) -> str:
    """Random token guaranteed fresh (PK collision is ~impossible; checked anyway)."""
    while True:
        token = secrets.token_hex(TOKEN_BYTES).upper()
        taken = session.execute(
            text("SELECT 1 FROM privacy_tokens WHERE token = :t"),
            {"t": token},
        ).first()
        if not taken:
            return token


def get_or_create_tokens(session: Session, kind: str, values: list) -> dict[str, str]:
    """Map each value to its token, minting rows for unseen identities.

    Returns {original_value: token}; blanks map to "" and are never stored.
    Race-safe: concurrent first-sees resolve to a single token per identity.
    """
    _check_kind(kind)
    vals = _check_values(values)
    out: dict[str, str] = {}
    # Dedupe (preserve order); blanks pass through untouched.
    ordered: list[str] = []
    for v in vals:
        if not v.strip():
            out[v] = ""
        elif v not in out and v not in ordered:
            ordered.append(v)
    if not ordered:
        return out

    norms = {v: normalize(v) for v in ordered}
    # Existing mappings (also repairs the in-request duplicate race window).
    rows = session.execute(
        text("SELECT norm, token FROM privacy_tokens WHERE kind = :k"),
        {"k": kind},
    ).fetchall()
    known = {r[0]: r[1] for r in rows}
    missing = [v for v in ordered if norms[v] not in known]
    for v in missing:
        session.execute(
            text(
                "INSERT INTO privacy_tokens (token, kind, norm, original) "
                "VALUES (:t, :k, :n, :o) ON CONFLICT (kind, norm) DO NOTHING"
            ),
            {"t": _mint_token(session), "k": kind, "n": norms[v], "o": v.strip()},
        )
    if missing:
        rows = session.execute(
            text("SELECT norm, token FROM privacy_tokens WHERE kind = :k"),
            {"k": kind},
        ).fetchall()
        known = {r[0]: r[1] for r in rows}
    for v in ordered:
        out[v] = known[norms[v]]
    session.flush()
    return out


def resolve_tokens(session: Session, tokens: list) -> dict[str, str | None]:
    """Map each token back to its original (None for unknown tokens).

    Blanks pass through as "". Lookup is case-insensitive (uppercased).
    """
    vals = _check_values([str(t) if t is not None else "" for t in (tokens or [])])
    out: dict[str, str | None] = {}
    wanted = sorted({v.upper() for v in vals if v.strip()})
    found: dict[str, str] = {}
    if wanted:
        # Chunked IN-list to stay well under parameter limits.
        for i in range(0, len(wanted), 500):
            chunk = wanted[i:i + 500]
            phs = ", ".join(f":t{j}" for j in range(len(chunk)))
            rows = session.execute(
                text(f"SELECT token, original FROM privacy_tokens WHERE token IN ({phs})"),
                {f"t{j}": t for j, t in enumerate(chunk)},
            ).fetchall()
            for r in rows:
                found[r[0]] = r[1]
    for v in vals:
        out[v] = found.get(v.upper()) if v.strip() else ""
    return out


def forget_tokens(session: Session, tokens: list) -> int:
    """Hard-delete mappings (unhash becomes impossible for them). Returns count."""
    vals = [v for v in _check_values([str(t) if t is not None else "" for t in (tokens or [])]) if v.strip()]
    if not vals:
        return 0
    total = 0
    upper = sorted({v.upper() for v in vals})
    for i in range(0, len(upper), 500):
        chunk = upper[i:i + 500]
        phs = ", ".join(f":t{j}" for j in range(len(chunk)))
        res = session.execute(
            text(f"DELETE FROM privacy_tokens WHERE token IN ({phs})"),
            {f"t{j}": t for j, t in enumerate(chunk)},
        )
        total += res.rowcount or 0
    session.flush()
    return total
