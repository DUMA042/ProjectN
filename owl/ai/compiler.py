"""Generic SQL compiler — recursive primitives over the IR, no per-question code.

Every identifier comes from the catalog; every value becomes a bound
parameter. The compiler cannot emit anything the validator did not already
approve, and the security validator re-checks the output independently.
Supports SELECT, WHERE (AND/OR/NOT), IN/NOT IN, BETWEEN, LIKE/ILIKE,
IS NULL, DISTINCT, ORDER BY, GROUP BY, HAVING, all five aggregates,
LIMIT/OFFSET, calculated expressions, and approved CASE. Subqueries, CTEs,
and window functions are parsed by ir2 but rejected unless enabled there —
this module implements no code paths for them yet by design.
"""
from __future__ import annotations

from owl.ai import catalog
from owl.ai.ir2 import IRValidationError


class _Ctx:
    def __init__(self, entity, fields):
        self.entity = entity
        self.fields = fields
        self.params: dict = {}
        self.n = 0
        self.joins: list[str] = []
        self.seen_joins: set[str] = set()

    def bind(self, value):
        name = f"p{self.n}"
        self.n += 1
        self.params[name] = value
        return f":{name}"

    def need_join(self, field):
        key = catalog.FIELD_JOINS.get(field)
        if key and key not in self.seen_joins:
            join = catalog.JOINS.get((self.entity, key))
            if join:
                self.joins.append(join)
                self.seen_joins.add(key)

    def col(self, field):
        spec = self.fields.get(field)
        if spec is None:
            raise IRValidationError(f"Unknown field '{field}'")
        self.need_join(field)
        return spec["column"]


def compile_expression(node, ctx):
    """Expression AST -> SQL fragment (literals become bound params)."""
    if set(node.keys()) == {"field"}:
        return ctx.col(node["field"])
    if set(node.keys()) == {"literal"}:
        return ctx.bind(node["literal"])
    op, args = node["op"], node.get("args", [])
    if op in ("+", "-", "*", "/"):
        if len(args) != 2:
            raise IRValidationError("Arithmetic needs exactly 2 args")
        left = compile_expression(args[0], ctx)
        right = compile_expression(args[1], ctx)
        return f"({left} {op} {right})"
    if op == "ROUND":
        if len(args) not in (1, 2):
            raise IRValidationError("ROUND needs 1..2 args")
        inner = ", ".join(compile_expression(a, ctx) for a in args)
        return f"ROUND({inner})"
    if op in ("COALESCE", "NULLIF"):
        if len(args) != 2:
            raise IRValidationError(f"{op} needs exactly 2 args")
        inner = ", ".join(compile_expression(a, ctx) for a in args)
        return f"{op}({inner})"
    if op == "EXTRACT_YEAR":
        return f"EXTRACT(YEAR FROM {compile_expression(args[0], ctx)})"
    if op == "EXTRACT_MONTH":
        return f"EXTRACT(MONTH FROM {compile_expression(args[0], ctx)})"
    if op == "DATE_TRUNC_MONTH":
        return f"date_trunc('month', {compile_expression(args[0], ctx)})"
    raise IRValidationError(f"Bad expression op '{op}'")


def compile_case(node, ctx):
    parts = []
    for w in node.get("whens", []):
        cond = compile_filter(w["when"], ctx)
        then = w["then"]
        if isinstance(then, dict):
            then_sql = compile_expression(then, ctx)
        else:
            then_sql = ctx.bind(then)
        parts.append(f"WHEN {cond} THEN {then_sql}")
    else_sql = ""
    if "else" in node:
        e = node["else"]
        else_sql = " ELSE " + (compile_expression(e, ctx) if isinstance(e, dict) else ctx.bind(e))
    return "(CASE " + " ".join(parts) + else_sql + " END)"


def compile_filter(node, ctx):
    """Filter AST -> SQL predicate (values always bound)."""
    if "and" in node:
        return "(" + " AND ".join(compile_filter(k, ctx) for k in node["and"]) + ")"
    if "or" in node:
        return "(" + " OR ".join(compile_filter(k, ctx) for k in node["or"]) + ")"
    if "not" in node:
        return f"(NOT ({compile_filter(node['not'], ctx)}))"
    field, op = node["field"], node["operator"]
    col = ctx.col(field)
    value = node.get("value")
    if op in ("IS NULL", "IS NOT NULL"):
        return f"{col} {op}"
    if op in ("IN", "NOT IN"):
        phs = ", ".join(ctx.bind(v) for v in value)
        return f"{col} {op} ({phs})"
    if op == "BETWEEN":
        lo, hi = value
        return f"{col} BETWEEN {ctx.bind(lo)} AND {ctx.bind(hi)}"
    return f"{col} {op} {ctx.bind(value)}"


AGG_SQL = {"COUNT": "COUNT", "COUNT DISTINCT": "COUNT(DISTINCT {c})",
           "SUM": "SUM", "AVG": "AVG", "MIN": "MIN", "MAX": "MAX"}


def compile_aggregate(item, ctx):
    func = item["aggregate"]
    sql = AGG_SQL[func]
    if "expression" in item:
        inner = compile_expression(item["expression"], ctx)
        if "DISTINCT" in func:
            return sql.format(c=inner)
        return f"{sql}({inner})"
    field = item["field"]
    if "DISTINCT" in func:
        return sql.format(c=ctx.col(field))
    if func == "COUNT" and field in ("*",):
        return "COUNT(*)"
    col = ctx.col(field)
    if func == "AVG" and ctx.fields[field]["pg_type"] == "time":
        # Postgres has no AVG(time): average epoch seconds instead. The
        # result column is numeric seconds-past-midnight, not a time.
        return f"AVG(EXTRACT(EPOCH FROM {col}))"
    return f"{sql}({col})"


def compile(ir):
    """Validated IR -> (parameterized SQL, params, meta).

    meta = {"tables": {...}, "aliases": {...}, "outputs": [...]}, describing
    exactly what was emitted, for the independent security validator.
    Single statement only."""
    entity = ir["source"]
    ent = catalog.ENTITIES[entity]
    ctx = _Ctx(entity, ent["fields"])

    # Explicitly requested joins (validated against the relationship registry).
    for j in ir.get("joins", []) or []:
        key = catalog.join_key_for(entity, j.get("table"))
        if key is None:
            raise IRValidationError(f"Relationship not approved: {entity} -> {j.get('table')}")
        if key not in ctx.seen_joins:
            join_sql = catalog.JOINS[(entity, key)]
            if j.get("type", "LEFT") == "INNER":
                join_sql = join_sql.replace("LEFT JOIN", "INNER JOIN", 1)
            ctx.joins.append(join_sql)
            ctx.seen_joins.add(key)

    out_names: dict[str, str] = {}
    select: list[str] = []
    for item in ir["select"]:
        if set(item.keys()) <= {"field", "alias"} and "aggregate" not in item and "expression" not in item and "case" not in item:
            name = item.get("alias") or item["field"]
            select.append(f'{ctx.col(item["field"])} AS "{name}"')
            out_names[name] = ctx.col(item["field"])
        elif "aggregate" in item:
            expr = compile_aggregate(item, ctx)
            select.append(f'{expr} AS "{item["alias"]}"')
            out_names[item["alias"]] = expr
        elif "expression" in item:
            expr = compile_expression(item["expression"], ctx)
            select.append(f'{expr} AS "{item["alias"]}"')
            out_names[item["alias"]] = expr
        elif "case" in item:
            expr = compile_case(item["case"], ctx)
            select.append(f'{expr} AS "{item["alias"]}"')
            out_names[item["alias"]] = expr

    # HAVING needs aggregate expressions addressable by alias.
    having_sql = None
    if ir.get("having") is not None:
        having_sql = _compile_having(ir["having"], ctx, out_names)

    order_parts = []
    for o in ir.get("order_by", []) or []:
        key = o["field"]
        expr = out_names.get(key) or (ctx.col(key) if key in ctx.fields else None)
        if expr is None:
            # group-by key not selected: resolve via its column.
            expr = ctx.col(key)
        order_parts.append(f"{expr} {'ASC' if o['direction'] == 'ASC' else 'DESC'}")

    # WHERE and GROUP BY can reference joined fields (department, location,
    # ...), which register their JOIN via ctx.col. They must be compiled
    # BEFORE the join list is flushed into the SQL below — otherwise the
    # predicate references a table alias with no JOIN in the statement.
    where_sql = None
    if ir.get("filters") is not None:
        where_sql = compile_filter(ir["filters"], ctx)
    group_by = ir.get("group_by", []) or []
    group_sql = ", ".join(ctx.col(g) for g in group_by) if group_by else None

    sql = f"SELECT {'DISTINCT ' if ir.get('distinct') else ''}{', '.join(select)} {ent['from']}"
    if ctx.joins:
        sql += " " + " ".join(ctx.joins)
    if where_sql is not None:
        sql += " WHERE " + where_sql
    if group_sql:
        sql += " GROUP BY " + group_sql
    if having_sql:
        sql += " HAVING " + having_sql
    if order_parts:
        sql += " ORDER BY " + ", ".join(order_parts)
    sql += f" LIMIT {ctx.bind(ir.get('limit', 100))} OFFSET {ctx.bind(ir.get('offset', 0))}"
    tables = set(catalog.ENTITY_BASE_TABLES.get(entity, (catalog.ENTITIES[entity]["table"],)))
    for key in ctx.seen_joins:
        tables.add(catalog.JOIN_TABLES[key])
    aliases = set(catalog.ENTITY_ALIASES.get(entity, set()))
    for key in ctx.seen_joins:
        if key in catalog.JOIN_ALIASES:
            aliases.add(catalog.JOIN_ALIASES[key])
    aliases.update(out_names.keys())
    return sql, ctx.params, {"tables": tables, "aliases": aliases, "outputs": list(out_names.keys())}


def _compile_having(node, ctx, out_names):
    """HAVING over group keys + select aliases (expressions inlined)."""
    if "and" in node:
        return "(" + " AND ".join(_compile_having(k, ctx, out_names) for k in node["and"]) + ")"
    if "or" in node:
        return "(" + " OR ".join(_compile_having(k, ctx, out_names) for k in node["or"]) + ")"
    if "not" in node:
        return f"(NOT ({_compile_having(node['not'], ctx, out_names)}))"
    key = node["field"]
    expr = out_names.get(key, ctx.col(key) if key in ctx.fields else None)
    if expr is None:
        raise IRValidationError(f"Cannot resolve HAVING field '{key}'")
    # Reuse leaf compilation against the resolved expression.
    op = node["operator"]
    value = node.get("value")
    if op in ("IS NULL", "IS NOT NULL"):
        return f"{expr} {op}"
    # Bind a throwaway param holder mirroring compile_filter leaf logic.
    if op in ("IN", "NOT IN"):
        phs = ", ".join(ctx.bind(v) for v in value)
        return f"{expr} {op} ({phs})"
    if op == "BETWEEN":
        lo, hi = value
        return f"{expr} BETWEEN {ctx.bind(lo)} AND {ctx.bind(hi)}"
    return f"{expr} {op} {ctx.bind(value)}"
