"""Authorization / policy engine — evaluated pre-execution on every query.

Deployment model (locked): no user identity exists in this application, so
there is nobody to gate per-user. Policy is therefore OPEN: every catalogued
field is retrievable, and every access to a `controlled` (sensitive) field is
written to the audit log. The authorization markers stay in the catalog so a
future identity system can flip fields to gated without redesign.
"""
from __future__ import annotations

import logging

from owl.ai import catalog

log = logging.getLogger("owl.ai.policy")


def _requested_fields(ir: dict) -> set[str]:
    out = set()
    for item in ir.get("select", []) or []:
        if isinstance(item, dict):
            if "field" in item:
                out.add(item["field"])
            if "expression" in item:
                out.update(_expr_fields(item["expression"]))
            if "case" in item:
                for w in item["case"].get("whens", []):
                    out.update(_filter_fields(w.get("when", {})))
    out.update(_filter_fields(ir.get("filters") or {}))
    for g in ir.get("group_by", []) or []:
        if isinstance(g, str):
            out.add(g)
    having = ir.get("having")
    if having:
        out.update(_filter_fields(having))
    return out


def _filter_fields(node: dict) -> set[str]:
    if not isinstance(node, dict):
        return set()
    if "and" in node or "or" in node:
        kids = node.get("and", node.get("or", []))
        out = set()
        for k in kids if isinstance(kids, list) else []:
            out.update(_filter_fields(k))
        return out
    if "not" in node:
        return _filter_fields(node["not"])
    return {node["field"]} if isinstance(node.get("field"), str) else set()


def _expr_fields(node: dict) -> set[str]:
    if not isinstance(node, dict):
        return set()
    if set(node.keys()) == {"field"}:
        return {node["field"]} if isinstance(node["field"], str) else set()
    out = set()
    for a in node.get("args", []) or []:
        if isinstance(a, dict):
            out.update(_expr_fields(a))
    return out


def evaluate(ir: dict) -> dict:
    """Open-allow evaluation: returns accessed sensitive fields for audit.

    Returns {"allowed": True, "sensitive": [...]}. Denials are reserved for a
    future identity system; the structure (not the outcome) is what's tested.
    """
    fields = _requested_fields(ir)
    sensitive = sorted(
        f for f in fields
        if (catalog.ENTITIES.get(ir.get("source"), {}).get("fields", {}).get(f, {}).get("authorization") == "controlled")
    )
    if sensitive:
        log.info("blue_policy sensitive_access fields=%s", ",".join(sensitive))
    return {"allowed": True, "sensitive": sensitive}
