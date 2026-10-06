"""BLUE pipeline: USER -> AI(IR) -> validate -> policy -> compile ->
security-validate -> read-only execute -> result contract -> narration gate.

The user message reaches the model verbatim (no input redaction layer). The
model never receives credentials, connections, tools, row data, or token
maps — only the reviewed catalog. All database interaction flows through the
controlled query API below. Audit records metadata only (hashes, counts,
intents — never values).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time

from sqlalchemy.orm import Session

from owl.ai import compiler
from owl.ai import deepseek
from owl.ai import ir2
from owl.ai import narrate
from owl.ai import policy
from owl.ai import router as _router
from owl.ai import secure_execute
from owl.ai import snapshot as _snapshot
from owl.ai import catalog as catalog_module

log = logging.getLogger("owl.ai.pipeline")


def _today_iso() -> str:
    from datetime import date

    return date.today().isoformat()


def _planner_system() -> str:
    return (
        "Your name is BLUE, the Flow HR reporting aide. "
        "You never see employee records — only the catalog below. "
        f"Today is {_today_iso()}. Resolve bare month names to YYYY-MM against that date. "
        "Respond with exactly one JSON object, no prose, no markdown. Routes:\n"
        '{"route": "chat", "reply": "..."} — greetings, opinions, non-data questions. '
        "Keep replies to 1-3 sentences.\n"
        '{"route": "clarify", "question": "..."} — the request is ambiguous (which person? '
        "which department? which month?). Ask ONE specific clarifying question, never guess.\n"
        '{"route": "query", "ir": {...}} — anything answerable from the database. '
        "IR shape: {source, select[], joins[], filters, group_by[], having, order_by[], "
        "limit, offset, distinct}. "
        "select items: {field} | {field, alias} | {aggregate, field|*, alias} | "
        "{aggregate, expression, alias} | {expression, alias} | {case, alias}. "
        "Filters: {field, operator, value} | {and:[...]} | {or:[...]} | {not:{...}}. "
        "Operators: =,!=,<,<=,>,>=,IN,NOT IN,BETWEEN,LIKE,ILIKE,IS NULL,IS NOT NULL. "
        "Aggregates: COUNT,COUNT DISTINCT,SUM,AVG,MIN,MAX. "
        "Request only needed columns; sensitive fields are delivered as placeholders "
        "you must repeat exactly ([NAME-1], [ID-1], ...). "
        "Prefer query over unsupported for anything about staff, attendance, leave, "
        "training, departments, rates, counts, or times. "
        '{"route": "unsupported"} — only for topics outside HR reporting, and ALWAYS '
        "for data-modification requests (delete, drop, update, insert, alter, truncate, grant — "
        "these can never be answered, only refused).\n"
        "EXAMPLE — top 5 HQ employees by working hours in August:\n"
        '{"route": "query", "ir": {"source": "attendance", '
        '"select": [{"field": "full_name"}, {"aggregate": "SUM", "field": "minutes_worked", "alias": "total_minutes"}], '
        '"filters": {"field": "location", "operator": "=", "value": "HQ"}, '
        '"group_by": ["full_name"], "order_by": [{"field": "total_minutes", "direction": "DESC"}], '
        '"limit": 5}}\n'
        "CATALOG (approved entities, fields, joins — the only vocabulary that exists):\n"
        f"{json.dumps(catalog_module.for_model(), default=str)}"
    )


import re as _re

# Data-modifying verbs: deterministic pre-screen (no model call needed, and the
# model can never authorize what this gate refuses). Word-boundary matched;
# common benign words (update, create, explain) are deliberately excluded —
# those are inexecutable through the IR anyway and handled by the planner.
_DESTRUCTIVE_RE = _re.compile(
    r"\b(delete|deleted|deleting|drop|dropped|truncate|truncating|grant|revoke|"
    r"alter|insert|merge|upsert|copy|vacuum)\b",
    _re.IGNORECASE,
)

READONLY_REFUSAL = (
    "I can't modify data — I'm read-only. Ask me about attendance, leave, "
    "training, departments, or rule settings instead."
)


def _audit(question: str, route: str, fields: list, row_count: int, ms: int, sensitive=None) -> None:
    log.info(
        "blue_ask q=%s route=%s fields=%s rows=%d ms=%d sensitive=%s",
        hashlib.sha256(question.encode()).hexdigest()[:16],
        route,
        ",".join(sorted(set(str(f) for f in fields))),
        row_count,
        ms,
        ",".join(sorted(sensitive or [])),
    )


def _parse_envelope(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ir2.IRValidationError("Planner did not return JSON")
    try:
        obj = json.loads(text[start:end + 1])
    except ValueError:
        raise ir2.IRValidationError("Planner returned malformed JSON")
    if not isinstance(obj, dict):
        raise ir2.IRValidationError("Planner output must be a JSON object")
    return obj


def _validate_route(obj: dict) -> dict:
    route = obj.get("route")
    if route == "chat":
        reply = obj.get("reply")
        if not isinstance(reply, str) or not reply.strip() or len(reply) > 2000:
            raise ir2.IRValidationError("chat route needs a short reply")
        return {"route": "chat", "reply": reply.strip()}
    if route == "clarify":
        question = obj.get("question")
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            raise ir2.IRValidationError("clarify route needs a question")
        return {"route": "clarify", "question": question.strip()}
    if route == "query":
        if not isinstance(obj.get("ir"), dict):
            raise ir2.IRValidationError("query route needs an ir object")
        return {"route": "query", "ir": ir2.validate(obj["ir"])}
    if route == "unsupported":
        return {"route": "unsupported"}
    raise ir2.IRValidationError(f"Unknown route '{route}'")


def _semantic_check(session: Session, ir: dict) -> None:
    """Existence probes for named departments/locations (values, not schema)."""
    from sqlalchemy import text as _text

    seen: set[tuple[str, str]] = set()

    def check(field: str, value: object) -> None:
        if field == "department" and isinstance(value, str):
            key = ("department", value.lower())
            if key in seen:
                return
            seen.add(key)
            hit = session.execute(
                _text("SELECT 1 FROM departments WHERE LOWER(department_name) = LOWER(:v)"),
                {"v": value},
            ).first()
            if not hit:
                raise ir2.IRValidationError(f"Unknown department '{value}'")
        elif field == "location" and isinstance(value, str):
            key = ("location", value.lower())
            if key in seen:
                return
            seen.add(key)
            hit = session.execute(
                _text("SELECT 1 FROM locations WHERE LOWER(location_name) = LOWER(:v)"),
                {"v": value},
            ).first()
            if not hit:
                raise ir2.IRValidationError(f"Unknown location '{value}'")

    def walk(node) -> None:
        if not isinstance(node, dict):
            return
        if "and" in node or "or" in node:
            for k in node.get("and", node.get("or", [])) or []:
                walk(k)
            return
        if "not" in node:
            walk(node["not"])
            return
        if "field" in node and "value" in node and isinstance(node.get("value"), str):
            check(node["field"], node["value"])

    if ir.get("filters") is not None:
        walk(ir["filters"])
    having = ir.get("having")
    if having is not None:
        walk(having)


def run_ask(
    session: Session,
    question: str,
    history: list[dict] | None = None,
    transport=None,
) -> dict:
    """One question through the full pipeline.

    Returns {answer, rows, columns, row_count, truncated, mode, sql?}.
    rows/columns hold REAL values for UI display only — never sent to a model.
    """
    from datetime import date as _date

    t0 = time.monotonic()
    ms_now = lambda: int((time.monotonic() - t0) * 1000)
    snap = _snapshot.load()

    # Deterministic destructive-intent screen: data modification is never
    # plannable, so refuse before any model call, router, or execution.
    if _DESTRUCTIVE_RE.search(question):
        _audit(question, "refused-destructive", [], 0, ms_now())
        return {
            "answer": READONLY_REFUSAL,
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }

    # Fast path: deterministic router (raw text, server-side, zero model cost).
    # Router envelopes carry IR v2 or direct answers.
    routed = None
    try:
        routed = _router.route(question, session, snap, _date.today())
    except Exception:  # noqa: BLE001 — router must never break the pipeline
        log.warning("blue_ask router failed")
        routed = None
    if routed is not None:
        if routed.get("type") == "direct":
            _audit(question, "router:direct", [], 0, ms_now())
            return {"answer": routed["answer"], "rows": [], "columns": [],
                    "row_count": 0, "truncated": False, "mode": "direct"}
        try:
            routed_ir = ir2.validate(routed["ir"])
        except ir2.IRValidationError:
            log.warning("blue_ask router produced invalid IR; falling through to model")
            routed = None
        else:
            return _execute_ir(session, question, routed_ir, routed.get("template"),
                               routed.get("period"), transport, t0, ms_now)

    # Model planning (blind: question + catalog only).
    system = _planner_system()
    msgs = [{"role": "user", "content": question.strip()}]
    raw = deepseek.chat(msgs, system=system, transport=transport)
    try:
        envelope = _validate_route(_parse_envelope(raw))
    except ir2.IRValidationError:
        _audit(question, "invalid", [], 0, ms_now())
        return {
            "answer": "I couldn't turn that into a safe query. Try rephrasing with a department, month, or smaller scope.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }

    if envelope["route"] == "chat":
        _audit(question, "chat", [], 0, ms_now())
        return {"answer": envelope["reply"], "rows": [], "columns": [],
                "row_count": 0, "truncated": False, "mode": "general"}
    if envelope["route"] == "clarify":
        _audit(question, "clarify", [], 0, ms_now())
        return {"answer": envelope["question"], "rows": [], "columns": [],
                "row_count": 0, "truncated": False, "mode": "clarify"}
    if envelope["route"] == "unsupported":
        _audit(question, "unsupported", [], 0, ms_now())
        return {
            "answer": "I can't answer that from data yet. Try asking about attendance, leave, training, departments, or rule settings.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }
    return _execute_ir(session, question, envelope["ir"], None, None, transport, t0, ms_now)


def _execute_ir(session, question, ir, template, period, transport, t0, ms_now):
    """Shared tail: policy -> compile -> secure execute -> narrate -> answer."""
    from owl.ai.catalog import ENTITIES

    # Policy (open-allow + sensitive-access audit).
    decision = policy.evaluate(ir)
    if not decision["allowed"]:
        _audit(question, "denied", [], 0, ms_now())
        return {
            "answer": "That request isn't permitted under the current data policy.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }

    # Compile.
    try:
        sql, params, meta = compiler.compile(ir)
    except ir2.IRValidationError as exc:
        _audit(question, "rejected", [], 0, ms_now())
        log.warning("blue_ask compile rejected: %s", type(exc).__name__)
        return {
            "answer": "I couldn't safely build that query. Try rephrasing with a department, month, or smaller scope.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }

    # Semantic existence checks (departments, locations).
    try:
        _semantic_check(session, ir)
    except ir2.IRValidationError:
        _audit(question, "rejected", [], 0, ms_now())
        return {
            "answer": "I couldn't find the department or location in that question. Check the spelling and try again.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }

    # Secure execute.
    try:
        result = secure_execute.run_validated(
            session, sql, params,
            tables=set(meta["tables"]),
            columns=catalog_module.bare_columns(),
            aliases=set(meta["aliases"]),
        )
    except (secure_execute.SecurityError, ValueError) as exc:
        _audit(question, "rejected", [], 0, ms_now())
        log.warning("blue_ask execution rejected: %s", type(exc).__name__)
        return {
            "answer": "I couldn't safely run that query. Try rephrasing with a department, month, or smaller scope.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "unsupported",
        }
    except Exception as exc:  # noqa: BLE001 — last resort; type only, never values
        _audit(question, "error", [], 0, ms_now())
        orig = getattr(exc, "orig", None)
        detail = type(orig).__name__ if orig is not None else type(exc).__name__
        code = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
        if code:
            detail = f"{detail}[{code}]"
        log.warning("blue_ask pipeline error: %s", detail)
        return {
            "answer": "BLUE hit an internal error running that question. Nothing was sent anywhere unexpected — please retry, and rephrase if it persists.",
            "rows": [], "columns": [], "row_count": 0, "truncated": False,
            "mode": "error",
        }

    rows = result["rows"]
    # Narration gate: provenance rule over output tiers.
    tiers = narrate.output_tiers(ir, ENTITIES[ir["source"]]["fields"])
    payload, sub_map = narrate.prepare(question, rows, {
        c for c, t in tiers.items() if t == "sensitive"
    })
    text = narrate.render(template, rows, period)
    if text is None:
        text = narrate.narrate(question, payload, transport=transport)
    answer = narrate.substitute(text, sub_map)
    _audit(question, f"query/{ir['source']}", list(tiers.keys()), len(rows), ms_now(), decision.get("sensitive", []))
    return {
        "answer": answer,
        "rows": rows,
        "columns": [{"name": c, "type": "text"} for c in result["columns"]],
        "row_count": result["row_count"],
        "truncated": result["truncated"],
        "mode": "data",
        "sql": sql,
    }
