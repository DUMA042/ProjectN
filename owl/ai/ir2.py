"""Query IR v2 — general-purpose, machine-validated read-only query language.

The model emits semantics, never SQL. There is deliberately NO `sql`, `raw`,
or free-text expression property: anything unrepresentable must extend the
IR/compiler deliberately, never smuggle strings through. Unknown keys are
rejected everywhere. Advanced capabilities (subqueries, CTEs, window
functions) parse but are gated off by default (phase 2).
"""
from __future__ import annotations

import re

from owl.ai import catalog
from owl.ai.catalog import NUM_OPS, TEXT_OPS

# Capability flags — phase 2 features stay rejected until deliberately enabled.
CAPABILITIES = {
    "subqueries": False,
    "ctes": False,
    "window": False,
}

OPERATORS = [
    "=", "!=", "<", "<=", ">", ">=",
    "IN", "NOT IN", "BETWEEN", "LIKE", "ILIKE",
    "IS NULL", "IS NOT NULL",
]
AGGS = ["COUNT", "COUNT DISTINCT", "SUM", "AVG", "MIN", "MAX"]
LOGIC = ("and", "or")
DIRECTIONS = ("ASC", "DESC")
JOIN_TYPES = ("INNER", "LEFT")
WINDOW_FUNCS = ("ROW_NUMBER", "RANK", "DENSE_RANK")
EXPR_OPS = ("+", "-", "*", "/", "ROUND", "COALESCE", "NULLIF",
            "EXTRACT_YEAR", "EXTRACT_MONTH", "DATE_TRUNC_MONTH")

MAX_LIMIT = 200
MAX_OFFSET = 5000
MAX_IN_LIST = 100
MAX_JOINS = 4
MAX_DEPTH = 3
MAX_CTES = 2

ALIAS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,60}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")


class IRValidationError(ValueError):
    """Raised when IR is malformed, unknown, mistyped, or disallowed."""


def _need(cond, msg):
    if not cond:
        raise IRValidationError(msg)


def _is_dict(v):
    return isinstance(v, dict)


def check_value(field_spec, operator, value, where):
    """Type-check one leaf value against the field's pg_type."""
    pg = field_spec["pg_type"]
    if operator in ("IS NULL", "IS NOT NULL"):
        _need(value is None, f"{where}: NULL check takes no value")
        return
    if operator in ("IN", "NOT IN"):
        _need(isinstance(value, list) and 1 <= len(value) <= MAX_IN_LIST,
              f"{where}: IN needs 1..{MAX_IN_LIST} items")
        for item in value:
            _check_scalar(field_spec, operator, item, where)
        return
    if operator == "BETWEEN":
        _need(isinstance(value, list) and len(value) == 2,
              f"{where}: BETWEEN needs exactly 2 values")
        for item in value:
            _check_scalar(field_spec, operator, item, where)
        return
    _check_scalar(field_spec, operator, value, where)


def _check_scalar(field_spec, operator, value, where):
    pg = field_spec["pg_type"]
    if pg == "integer":
        _need(isinstance(value, int) and not isinstance(value, bool),
              f"{where}: expected integer for {field_spec.get('name', '?')}")
    elif pg == "numeric":
        _need(isinstance(value, (int, float)) and not isinstance(value, bool),
              f"{where}: expected number")
    elif pg == "date":
        _need(isinstance(value, str) and DATE_RE.match(value),
              f"{where}: expected YYYY-MM-DD date")
    elif pg == "time":
        _need(isinstance(value, str) and TIME_RE.match(value),
              f"{where}: expected HH:MM[:SS] time")
    else:  # text and anything else
        _need(isinstance(value, str), f"{where}: expected string")
    if operator in ("LIKE", "ILIKE"):
        _need(pg == "text", f"{where}: LIKE needs a text field")


def check_filter(node, fields, depth, where="filters"):
    """Recursive filter validation (depth-capped)."""
    _need(depth <= MAX_DEPTH, f"{where}: nesting too deep (max {MAX_DEPTH})")
    _need(_is_dict(node), f"{where}: each filter must be an object")
    keys = set(node.keys())
    if keys == {"and"} or keys == {"or"}:
        kids = node["and"] if "and" in node else node["or"]
        _need(isinstance(kids, list) and 1 <= len(kids) <= 10,
              f"{where}: logic needs 1..10 children")
        for i, kid in enumerate(kids):
            check_filter(kid, fields, depth + 1, f"{where}[{i}]")
        return
    if keys == {"not"}:
        check_filter(node["not"], fields, depth + 1, f"{where}.not")
        return
    _need(set(node.keys()) <= {"field", "operator", "value"},
          f"{where}: unknown filter keys {sorted(keys)}")
    _need("field" in node and "operator" in node, f"{where}: leaf needs field+operator")
    name, op = node["field"], node["operator"]
    _need(name in fields, f"{where}: unknown field '{name}'")
    _need(op in OPERATORS, f"{where}: bad operator '{op}'")
    _need(op in fields[name]["operators"] or op in ("IS NULL", "IS NOT NULL"),
          f"{where}: operator '{op}' not allowed on '{name}'")
    check_value(fields[name], op, node.get("value"), where)


def check_expression(node, fields, depth, where="expression"):
    _need(depth <= MAX_DEPTH, f"{where}: nesting too deep")
    _need(_is_dict(node), f"{where}: expression must be an object")
    if set(node.keys()) == {"field"}:
        _need(node["field"] in fields, f"{where}: unknown field '{node['field']}'")
        return
    if set(node.keys()) == {"literal"}:
        _need(isinstance(node["literal"], (str, int, float)) and not isinstance(node["literal"], bool),
              f"{where}: bad literal")
        return
    _need(set(node.keys()) <= {"op", "args"}, f"{where}: bad expression keys")
    _need(node.get("op") in EXPR_OPS, f"{where}: bad expression op")
    args = node.get("args", [])
    _need(isinstance(args, list) and 1 <= len(args) <= 3, f"{where}: bad args")
    for i, a in enumerate(args):
        check_expression(a, fields, depth + 1, f"{where}[{i}]")


def _expr_fields(node, out):
    """Collect field names referenced by an expression AST."""
    if not isinstance(node, dict):
        return
    if set(node.keys()) == {"field"} and isinstance(node.get("field"), str):
        out.add(node["field"])
    for a in node.get("args", []) or []:
        if isinstance(a, dict):
            _expr_fields(a, out)


def check_case(node, fields, where="case"):
    _need(_is_dict(node) and set(node.keys()) <= {"whens", "else"}, f"{where}: bad CASE shape")
    whens = node.get("whens", [])
    _need(isinstance(whens, list) and 1 <= len(whens) <= 5, f"{where}: need 1..5 WHENs")
    for i, w in enumerate(whens):
        _need(_is_dict(w) and set(w.keys()) == {"when", "then"}, f"{where}: bad WHEN")
        check_filter(w["when"], fields, 1, f"{where}[{i}].when")
        then = w["then"]
        _need(isinstance(then, (str, int, float)) and not isinstance(then, bool),
              f"{where}: THEN must be a literal")
    if "else" in node:
        _need(isinstance(node["else"], (str, int, float)) and not isinstance(node["else"], bool),
              f"{where}: ELSE must be a literal")


def check_select_item(item, fields, where="select"):
    _need(_is_dict(item), f"{where}: each item must be an object")
    keys = set(item.keys())
    if keys == {"field"} or keys == {"field", "alias"}:
        _need(item["field"] in fields, f"{where}: unknown field '{item['field']}'")
        if "alias" in item:
            _need(isinstance(item["alias"], str) and ALIAS_RE.match(item["alias"]),
                  f"{where}: bad alias")
        return
    if set(keys) <= {"aggregate", "field", "alias"} and "aggregate" in keys:
        _need(item["aggregate"] in AGGS, f"{where}: bad aggregate")
        if item["field"] == "*":
            _need(item["aggregate"] in ("COUNT", "COUNT DISTINCT"),
                  f"{where}: * only valid with COUNT")
        else:
            _need(item["field"] in fields, f"{where}: unknown field")
            _need(item["aggregate"] in fields[item["field"]]["aggregatable"],
                  f"{where}: {item['aggregate']} not allowed on {item['field']}")
        _need(isinstance(item.get("alias"), str) and ALIAS_RE.match(item["alias"]),
              f"{where}: aggregates need a valid alias")
        return
    if set(keys) <= {"aggregate", "expression", "alias"} and "aggregate" in keys:
        _need(item["aggregate"] in AGGS, f"{where}: bad aggregate")
        check_expression(item["expression"], fields, 1, f"{where}.expression")
        _need(isinstance(item.get("alias"), str) and ALIAS_RE.match(item["alias"]),
              f"{where}: aggregates need a valid alias")
        return
    if ("expression" in keys or "case" in keys) and set(keys) <= {"expression", "case", "alias"}:
        _need("alias" in item and isinstance(item["alias"], str) and ALIAS_RE.match(item["alias"]),
              f"{where}: calculated items need a valid alias")
        if "expression" in item:
            check_expression(item["expression"], fields, 1, where)
        else:
            check_case(item["case"], fields, where)
        return
    raise IRValidationError(f"{where}: bad select item {sorted(keys)}")


def validate(ir):
    """Validate raw model output into a normalized executable IR dict."""
    _need(_is_dict(ir), "IR must be a JSON object")
    allowed = {"source", "select", "joins", "filters", "group_by", "having",
               "order_by", "limit", "offset", "distinct",
               "subqueries", "ctes", "window"}
    unknown = set(ir.keys()) - allowed
    _need(not unknown, f"Unknown IR keys: {sorted(unknown)}")

    source = ir.get("source")
    _need(source in catalog.ENTITIES, f"Unknown source '{source}'")
    ent = catalog.ENTITIES[source]
    fields = ent["fields"]

    select = ir.get("select", [])
    _need(isinstance(select, list) and 1 <= len(select) <= 20, "select needs 1..20 items")
    for i, item in enumerate(select):
        check_select_item(item, fields, f"select[{i}]")

    joins = ir.get("joins", []) or []
    _need(isinstance(joins, list) and len(joins) <= MAX_JOINS, f"joins: max {MAX_JOINS}")
    seen_joins = set()
    for i, j in enumerate(joins):
        _need(_is_dict(j) and set(j.keys()) <= {"table", "type"},
              f"joins[{i}]: need table+type")
        target = j.get("table")
        _need(isinstance(target, str) and target in catalog.CATALOG_TABLES,
              f"joins[{i}]: unknown table")
        _need(j.get("type", "LEFT") in JOIN_TYPES, f"joins[{i}]: bad join type")
        _need(target != catalog.ENTITIES[source]["table"],
              f"joins[{i}]: cannot join source to itself")
        key = catalog.join_key_for(source, target)
        _need(key is not None, f"joins[{i}]: relationship not approved")
        _need(key not in seen_joins, f"joins[{i}]: duplicate join")
        seen_joins.add(key)

    filters = ir.get("filters")
    if filters is not None:
        check_filter(filters, fields, 0)

    group_by = ir.get("group_by", []) or []
    _need(isinstance(group_by, list) and len(group_by) <= 10, "group_by: max 10")
    for g in group_by:
        _need(g in fields, f"group_by: unknown field '{g}'")
    has_agg = any(isinstance(item, dict) and "aggregate" in item for item in select)
    if has_agg:
        bare = [
            item["field"] for item in select
            if isinstance(item, dict) and set(item.keys()) <= {"field", "alias"}
        ]
        for b in bare:
            _need(b in group_by, f"aggregated query must GROUP BY selected field '{b}'")

    having = ir.get("having")
    if having is not None:
        # HAVING reuses filter grammar over group keys + aggregate aliases.
        hfields = dict(fields)
        for item in select:
            if not (isinstance(item, dict) and "aggregate" in item and "alias" in item):
                continue
            if item.get("field") == "*":
                agg_type = "integer"
            elif isinstance(item.get("field"), str):
                base = fields[item["field"]]
                agg_type = "integer" if item["aggregate"] in ("COUNT", "COUNT DISTINCT") else base["pg_type"]
            else:
                refs: set[str] = set()
                _expr_fields(item.get("expression", {}), refs)
                ref_types = {fields.get(f, {}).get("pg_type") for f in refs}
                agg_type = "numeric" if ref_types and ref_types <= {"integer", "numeric"} else "text"
            hfields[item["alias"]] = {
                "operators": NUM_OPS if agg_type in ("integer", "numeric") else TEXT_OPS,
                "pg_type": agg_type, "name": item["alias"],
            }
        check_filter(having, hfields, 0, "having")

    order_by = ir.get("order_by", []) or []
    _need(isinstance(order_by, list) and len(order_by) <= 5, "order_by: max 5")
    outputs = set()
    for i, item in enumerate(select):
        if not isinstance(item, dict):
            continue
        outputs.add(item.get("alias") or item.get("field") or f"col{i}")
    orderable = outputs | set(group_by)
    for i, o in enumerate(order_by):
        _need(_is_dict(o) and set(o.keys()) == {"field", "direction"},
              f"order_by[{i}]: need field+direction")
        _need(o["direction"] in DIRECTIONS, f"order_by[{i}]: bad direction")
        _need(o["field"] in orderable,
              f"order_by[{i}]: must reference a selected output or group key")

    limit = ir.get("limit", 100)
    _need(isinstance(limit, int) and not isinstance(limit, bool) and 1 <= limit <= MAX_LIMIT,
          f"limit must be 1..{MAX_LIMIT}")
    offset = ir.get("offset", 0)
    _need(isinstance(offset, int) and not isinstance(offset, bool) and 0 <= offset <= MAX_OFFSET,
          f"offset must be 0..{MAX_OFFSET}")
    distinct = ir.get("distinct", False)
    _need(isinstance(distinct, bool), "distinct must be boolean")

    for gated, name in (("subqueries", "subqueries"), ("ctes", "CTEs"), ("window", "window functions")):
        val = ir.get(gated)
        present = bool(val) if not isinstance(val, list) else len(val) > 0
        if present and not CAPABILITIES[gated]:
            raise IRValidationError(f"{name} are not enabled in this phase")
        if gated == "window" and isinstance(val, dict):
            _check_window(val, fields)

    return {
        "source": source,
        "select": select,
        "joins": [{"table": j.get("table"), "type": j.get("type", "LEFT")} for j in joins],
        "filters": filters,
        "group_by": list(group_by),
        "having": having,
        "order_by": [{"field": o["field"], "direction": o["direction"]} for o in order_by],
        "limit": limit,
        "offset": offset,
        "distinct": distinct,
        "subqueries": [],
        "ctes": [],
        "window": None,
    }


def _check_window(node, fields):
    _need(_is_dict(node), "window must be an object")
    _need(node.get("function") in WINDOW_FUNCS, "window: bad function")
    for key in ("partition_by",):
        for g in node.get(key, []) or []:
            _need(g in fields, f"window: unknown field '{g}'")
    ob = node.get("order_by", []) or []
    for o in ob:
        _need(_is_dict(o) and o.get("field") in fields, "window: bad order_by")
        _need(o.get("direction") in DIRECTIONS, "window: bad direction")
    _need(isinstance(node.get("alias"), str) and ALIAS_RE.match(node.get("alias")),
          "window: need a valid alias")
