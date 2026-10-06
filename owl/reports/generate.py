"""Per-topic AI report generation + chart-spec rendering.

Each included topic gets its own model completion (keeps every call inside
the provider timeout), with a word budget derived from the confirmed range
and the focus weights. The model returns markdown plus structured chart
specs; specs are validated and rendered server-side with matplotlib, so the
model never fabricates image bytes and every visual comes from supplied data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from owl.ai import deepseek

FOCUS_WEIGHT = {"low": 1, "medium": 2, "high": 3}
FOCUS_GUIDANCE = {
    "low": "Brief summary and key figures only. Keep it tight.",
    "medium": "Summary, trends, interpretation, and supporting figures.",
    "high": "Detailed analysis: breakdowns, trends, comparisons, insights, and supporting figures.",
}

CHART_TYPES = ("bar", "line", "donut")
MAX_CHARTS = 6
MAX_CHART_POINTS = 12
MAX_TOTAL_CHARTS = 12

ACCENT = "#1677FF"
PALETTE = ["#1677FF", "#00B578", "#FF8A00", "#B657FF", "#FF5C5C", "#00B8D9", "#7A7A7A"]

GENERATION_SYSTEM = """You write one section of a professional HR report for managers. Rules:
- Plain, clear English. Headings with ##, sub-headings with ###, tables in markdown, \
key figures in bold. No technical jargon about data tooling.
- REPORT THE DATA, never the file: write about employees, departments, and trends — \
never about rows, columns, samples, missing fields, or what "cannot be computed". \
If a figure is unavailable, omit it silently or state the finding in one short clause; \
a one-line scope note per section is the maximum file talk allowed.
- Use ONLY the supplied EXACT FACTS. Quote their figures directly — never estimate from \
samples. If a figure is unavailable, omit it silently per the rule above.
- Every percentage MUST include its real figure, e.g. 83.3% (50 of 60 employees).
- Every section MUST contain: (1) a key-figures table; (2) a trend statement with direction \
and magnitude, plus a line/bar visual wherever the data has a time dimension; (3) grouped \
breakdowns — departmental breakdown is MANDATORY in every section (table or chart), plus \
grade/rank, sex, employment-type splits wherever supported; (4) a Recommendations part with \
concrete HR actions tied to the figures; (5) at least one positive callout (best department, \
improving trend, strong compliance) — report good news alongside problems.
- Hashed values (32-char hex codes) are simply employee names: list them in tables and \
rankings naturally (e.g. "Top 5 late arrivals"), exactly as you would real names. Never \
mention hashing, tokens, or anonymization mechanics to the reader, and never try to \
reverse them.
- Stay near the word target. No padding.
- Do NOT start with a top-level heading for the section: the section title is supplied \
separately. Begin with ## sub-headings or body text.
After the markdown, append ONE fenced block exactly like:
```charts
[{"type": "bar|line|donut", "title": str, "labels": [str, ...], "values": [number, ...]}]
```
At most 3 charts, only where a visual adds insight — grouped breakdowns (e.g. late \
arrivals by department) and trends count as insightful. Charts must use figures from your \
section. If no chart is warranted, write ```charts\\n[]\\n```.
Also wrap 3-5 headline numbers in ONE fenced block like:
```kpi
Attendance rate: 83.3% (50 of 60 employees)
Late arrivals: 10
```
One fact per line, "label: value" format, values with real figures."""


def word_budgets(
    topics: list[dict[str, Any]], min_words: int, max_words: int
) -> dict[str, int]:
    """Split the range midpoint across topics by focus weight.

    Scaled x1.4 for the mandated structure (tables, comparisons, visuals):
    richer required content needs headroom beyond the bare range.
    """
    weights = [FOCUS_WEIGHT.get(t.get("focus", "medium"), 2) for t in topics]
    total = sum(weights) or 1
    mid = round((min_words + max_words) // 2 * 1.4)
    return {
        t["name"]: max(120, round(mid * w / total)) for t, w in zip(topics, weights)
    }


def generate_topic_section(
    topic: dict[str, Any],
    budget_words: int,
    pack: str,
    hash_mode: str | None,
    grouping: str = "",
    facts_text: str = "",
    understanding: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """One completion -> (markdown, validated chart specs)."""
    dims = topic.get("dimensions") or []
    user = (
        f"TOPIC: {topic['name']} (focus: {topic.get('focus', 'medium')}). "
        f"{FOCUS_GUIDANCE.get(topic.get('focus', 'medium'), '')}\n"
        f"Word target: about {budget_words} words.\n"
        f"HASHING: {hash_mode or 'none'}.\n"
        + (f"SUPPORTED GROUPINGS for this topic: {', '.join(dims)}. "
           if dims else "")
        + (f"GROUPING RULES: {grouping}\n" if grouping else "")
        + (f"{understanding}\n" if understanding else "")
        + (f"EXACT FACTS (quote these figures, never estimate):\n{facts_text}\n"
           if facts_text else "")
        + f"DATA PROFILES:\n{pack}"
    )
    reply = deepseek.chat([{"role": "user", "content": user}], system=GENERATION_SYSTEM)
    return split_charts(reply)


def split_charts(reply: str) -> tuple[str, list[dict[str, Any]], list[tuple[str, str]]]:
    """Separate markdown from the trailing charts + KPI fences; validate specs.

    Returns (markdown, specs, kpis) with both fences stripped from the text.
    """
    kpis: list[tuple[str, str]] = []
    kpi_match = re.search(r"```kpi\s*(.*?)\s*```", reply, re.DOTALL)
    if kpi_match:
        for line in kpi_match.group(1).splitlines():
            if ":" in line:
                label, value = line.split(":", 1)
                if label.strip() and value.strip():
                    kpis.append((label.strip()[:60], value.strip()[:120]))
            if len(kpis) >= 5:
                break
        reply = (reply[: kpi_match.start()] + reply[kpi_match.end():]).strip()
    m = re.search(r"```charts\s*(\[.*?\])\s*```", reply, re.DOTALL)
    specs: list[dict[str, Any]] = []
    markdown = reply
    if m:
        markdown = (reply[: m.start()] + reply[m.end():]).strip()
        try:
            raw = json.loads(m.group(1))
        except ValueError:
            raw = []
        if isinstance(raw, list):
            for s in raw[:MAX_CHARTS]:
                clean = validate_chart_spec(s)
                if clean is not None:
                    specs.append(clean)
    return markdown, specs, kpis


def chart_key(spec: dict[str, Any]) -> tuple:
    return (spec["type"], tuple(sorted(str(x).lower() for x in spec["labels"])))


def dedupe_specs(
    specs: list[dict[str, Any]], existing: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Drop specs duplicating an already-rendered chart (same type + labels)."""
    seen = {chart_key(s) for s in existing}
    out = []
    for s in specs:
        key = chart_key(s)
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def mandated_visuals(topic_name: str, fact_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backend-computed mandatory charts for a topic (no model judgment).

    Department comparison bar, trend line, and composition donut — built from
    exact facts so the guaranteed comparisons always exist. Pure + testable.
    """
    specs: list[dict[str, Any]] = []
    for facts in fact_list:
        ranking = facts.get("department_ranking") or []
        if ranking:
            top = ranking[:8]
            specs.append({
                "type": "bar",
                "title": f"{topic_name} by department",
                "labels": [r["group"] for r in top],
                "values": [float(r["count"]) for r in top],
            })
        for col, points in (facts.get("trends") or {}).items():
            if len(points) >= 2:
                specs.append({
                    "type": "line",
                    "title": f"{topic_name} trend ({col})",
                    "labels": [p["period"] for p in points],
                    "values": [float(p["count"]) for p in points],
                })
                break
        for col, rows in (facts.get("top_values") or {}).items():
            if 2 <= len(rows) <= 8:
                specs.append({
                    "type": "donut",
                    "title": f"{topic_name} composition ({col})",
                    "labels": [r["value"] for r in rows],
                    "values": [float(r["count"]) for r in rows],
                })
                break
        if len(specs) >= 3:
            break
    valid = []
    for s in specs[:3]:
        clean = validate_chart_spec(s)
        if clean is not None:
            valid.append(clean)
    return valid


def validate_chart_spec(spec: Any) -> dict[str, Any] | None:
    """Strict shape check; None means skip the chart (never fail the build)."""
    if not isinstance(spec, dict):
        return None
    if spec.get("type") not in CHART_TYPES:
        return None
    labels = spec.get("labels")
    values = spec.get("values")
    title = str(spec.get("title", "")).strip()
    if not title or not isinstance(labels, list) or not isinstance(values, list):
        return None
    if not labels or len(labels) != len(values) or len(labels) > MAX_CHART_POINTS:
        return None
    try:
        nums = [float(v) for v in values]
    except (TypeError, ValueError):
        return None
    return {
        "type": spec["type"],
        "title": title[:120],
        "labels": [str(x)[:40] for x in labels],
        "values": nums,
    }


def render_chart(spec: dict[str, Any], path: Path) -> None:
    """Chart spec -> PNG file (Agg backend, no display needed)."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels, values = spec["labels"], spec["values"]
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    if spec["type"] == "bar":
        bars = ax.bar(labels, values, color=colors)
        ax.set_ylabel("Value")
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}",
                    ha="center", va="bottom", fontsize=8)
    elif spec["type"] == "line":
        ax.plot(labels, values, color=ACCENT, marker="o")
        ax.set_ylabel("Value")
        for x, v in zip(labels, values):
            ax.text(x, v, f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}",
                    ha="center", va="bottom", fontsize=8)
    else:  # donut
        wedges, _, autotexts = ax.pie(
            values, colors=colors, startangle=90,
            autopct=lambda p: f"{p:.1f}%",
            pctdistance=0.8,
            wedgeprops={"width": 0.42, "edgecolor": "white"},
        )
        for t in autotexts:
            t.set_fontsize(8)
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
    ax.set_title(spec["title"], fontsize=11, fontweight="bold")
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
