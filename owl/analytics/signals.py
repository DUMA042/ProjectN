"""Cross-subject signal engine for the Pulse tab.

Computes segment-level current-vs-previous deltas across a curated set of
(subject, metric, dimension) combos, z-scores each delta against its sibling
segments, and returns the most notable movements as ranked "signals" — each
carrying the filter that diagnoses it. Data-health items (fact freshness,
coverage, quarantine backlog) ride along in the same response.
"""
from __future__ import annotations

from datetime import date, timedelta

from owl.analytics.engine import run_explore
from owl.analytics.metrics import DOMAIN_METRICS
from owl.analytics.today import freshness_snapshot

# (domain, metric, dimensions) combos worth watching.
COMBOS: list[tuple[str, str, list[str]]] = [
    ("attendance", "attendance_rate", ["department", "grade_level", "employment_type", "rank"]),
    ("attendance", "absence_rate", ["department", "grade_level", "employment_type", "rank"]),
    ("attendance", "late_arrivals", ["department", "grade_level", "employment_type", "rank"]),
    ("leave", "unique_staff", ["department"]),
]

# Employee-level absolute thresholds that are always newsworthy.
EMPLOYEE_THRESHOLDS = [
    ("attendance", "absent_days", 10, "absent days"),
    ("attendance", "late_arrivals", 10, "late arrivals"),
]

MAX_PER_COMBO = 2
MAX_PER_DIMENSION = 3


def _default_window() -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=89)
    return start.isoformat(), end.isoformat()


def _prev_window(sd: str, ed: str) -> tuple[str, str]:
    s, e = date.fromisoformat(sd), date.fromisoformat(ed)
    length = (e - s).days + 1
    pe = s - timedelta(days=1)
    ps = pe - timedelta(days=length - 1)
    return ps.isoformat(), pe.isoformat()


def _groups_by_segment(explore_result: dict, dim: str) -> dict:
    return {str(g[dim]): g for g in explore_result.get("groups", []) if g.get(dim) is not None}


def _severity(pp: float | None, pct_change: float | None, current: float) -> str:
    if pp is not None:
        if abs(pp) >= 10:
            return "danger"
        if abs(pp) >= 4:
            return "warning"
        return "info"
    if pct_change is not None:
        if current >= 5 and abs(pct_change) >= 50:
            return "danger"
        if current >= 3 and abs(pct_change) >= 25:
            return "warning"
    return "info"


def _metric_meta(domain: str, metric: str) -> dict:
    return DOMAIN_METRICS[domain][metric]


def compute_signals(date_range: dict | None, filters: dict | None, limit: int = 12) -> dict:
    sd = (date_range or {}).get("start")
    ed = (date_range or {}).get("end")
    if not sd or not ed:
        sd, ed = _default_window()
    psd, ped = _prev_window(sd, ed)

    signals: list[dict] = []
    per_dimension: dict[str, int] = {}

    def explore(domain, metric, dim, dr):
        return run_explore(
            domain=domain, metrics=[metric], group_by=[dim], filters=filters,
            date_range=dr, mode="summary", page=1, page_size=500,
        )

    for domain, metric, dims in COMBOS:
        meta = _metric_meta(domain, metric)
        is_rate = meta.get("type") == "pct"
        for dim in dims:
            cur = _groups_by_segment(explore(domain, metric, dim, {"start": sd, "end": ed}), dim)
            prev = _groups_by_segment(explore(domain, metric, dim, {"start": psd, "end": ped}), dim)
            if not cur and not prev:
                continue

            candidates = []
            for seg, row in cur.items():
                p = prev.get(seg)
                cval = row.get(metric)
                if cval is None:
                    continue
                pval = p.get(metric) if p else None
                if pval is None:
                    # Segment is new in this window — only interesting at scale.
                    if is_rate or cval < 5:
                        continue
                    delta_pp, pct_change = None, 100.0
                else:
                    delta_pp = round(float(cval) - float(pval), 1) if is_rate else None
                    pct_change = (
                        round(100.0 * (float(cval) - float(pval)) / float(pval), 1)
                        if float(pval) > 0 else (100.0 if float(cval) > 0 else 0.0)
                    )
                if delta_pp == 0 and (pct_change in (0.0, None)):
                    continue
                candidates.append({
                    "dimension": dim, "segment": seg, "domain": domain, "metric": metric,
                    "metric_label": meta["label"], "type": meta.get("type", "int"),
                    "polarity": meta.get("polarity"),
                    "current": cval, "previous": pval,
                    "delta_pp": delta_pp, "pct_change": pct_change,
                })

            if len(candidates) < 2:
                continue
            # z-score deltas across sibling segments in this combo
            values = [c["delta_pp"] if c["delta_pp"] is not None else c["pct_change"] for c in candidates]
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / len(values)
            std = var ** 0.5 or 1.0

            for c in candidates:
                raw = c["delta_pp"] if c["delta_pp"] is not None else c["pct_change"]
                z = round((raw - mean) / std, 2)
                sev = _severity(c["delta_pp"], c["pct_change"], float(c["current"]))
                notable = abs(z) >= 1.2 or sev in ("danger", "warning")
                if not notable:
                    continue
                direction = "up" if raw > 0 else "down"
                # "good" when the movement aligns with the metric's polarity
                good = None
                if c.get("polarity") in ("up_good", "up_bad"):
                    good = (direction == "up") == (c["polarity"] == "up_good")
                unit = "pp" if c["delta_pp"] is not None else "%"
                cur_fmt = f"{c['current']}%" if is_rate else c["current"]
                prev_fmt = f"{c['previous']}%" if (is_rate and c["previous"] is not None) else (c["previous"] if c["previous"] is not None else "new")
                delta_txt = f"{raw:+g}{unit}"
                signals.append({
                    **c,
                    "z": z,
                    "severity": sev if sev != "info" else ("warning" if abs(z) >= 1.8 else "info"),
                    "direction": direction,
                    "good": good,
                    "headline": f"{seg} · {meta['label'].lower()} {prev_fmt} → {cur_fmt} ({delta_txt})",
                    "detail": f"vs previous period ({psd} → {ped}) · z {z:+g}",
                    "drill": {"dimension": dim, "value": seg},
                    "_score": ({"danger": 3, "warning": 2, "info": 1}[sev]) * (1 + abs(z)),
                })
                per_dimension[dim] = per_dimension.get(dim, 0) + 1

    # Employee threshold crossings
    for domain, metric, threshold, noun in EMPLOYEE_THRESHOLDS:
        res = run_explore(
            domain=domain, metrics=[metric], group_by=["employee", "employee_id"],
            filters=filters, date_range={"start": sd, "end": ed},
            mode="summary", page=1, page_size=200, sort_by=metric, sort_dir="desc",
        )
        for g in res.get("groups", []):
            if (g.get(metric) or 0) < threshold:
                break
            if per_dimension.get("employee", 0) >= 2:
                break
            name = g.get("employee") or g.get("employee_id")
            signals.append({
                "dimension": "employee", "segment": name,
                "domain": domain, "metric": metric, "metric_label": _metric_meta(domain, metric)["label"],
                "current": g[metric], "previous": None, "delta_pp": None, "pct_change": None,
                "z": None, "severity": "warning", "direction": "up", "good": False,
                "headline": f"{name} crossed {threshold} {noun} this period",
                "detail": f"{g[metric]} {noun} between {sd} and {ed}",
                "drill": {"dimension": "employee_id", "value": g.get("employee_id")},
                "_score": 2.5,
            })
            per_dimension["employee"] = per_dimension.get("employee", 0) + 1

    # Rank, cap per dimension, trim
    signals.sort(key=lambda s: s["_score"], reverse=True)
    capped: list[dict] = []
    counts: dict[str, int] = {}
    for s in signals:
        d = s["dimension"]
        if counts.get(d, 0) >= MAX_PER_DIMENSION:
            continue
        counts[d] = counts.get(d, 0) + 1
        s.pop("_score", None)
        capped.append(s)
        if len(capped) >= limit:
            break

    return {
        "as_of": date.today().isoformat(),
        "window": {"start": sd, "end": ed},
        "previous_window": {"start": psd, "end": ped},
        "signals": capped,
        "health": freshness_snapshot(filters),
    }
