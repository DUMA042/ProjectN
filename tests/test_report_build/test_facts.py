"""Server-side fact packs: exact aggregates over full files (pure)."""
from __future__ import annotations

from owl.reports.facts import cross_tab, fact_pack, histogram_bins, render_facts, top_n, trend

CSV = (
    "full_name,department,sex,status,work_date,days_present\n"
    "Alice Ama,HR,Female,present,2026-06-02,20\n"
    "Bob Boateng,IT,Male,late,2026-06-03,18\n"
    "Cara Dan,IT,Female,present,2026-07-04,20\n"
    "Dan Efe,HR,Male,absent,2026-07-05,0\n"
)


def test_cross_tab_exact_counts_and_shares():
    from owl.reports.facts import _read
    df = _read(CSV)
    rows = cross_tab(df, "department")
    assert [(r["group"], r["count"]) for r in rows] == [("HR", 2), ("IT", 2)]
    assert rows[0]["share"] == "50.0% (2 of 4)"


def test_trend_month_buckets_with_change():
    from owl.reports.facts import _read
    df = _read(CSV)
    t = trend(df, "work_date")
    assert [r["period"] for r in t] == ["2026-06", "2026-07"]
    assert t[1]["change_pct"] == 0.0


def test_histogram_bins_cover_all_rows():
    from owl.reports.facts import _read
    df = _read(CSV)
    bins = histogram_bins(df, "days_present")
    assert sum(b["count"] for b in bins) == 4


def test_fact_pack_has_mandatory_anchors():
    f = fact_pack("att.csv", CSV)
    assert f["rows"] == 4
    assert "department" in f["by_group"] and "sex" in f["by_group"]
    assert f["department_ranking"][0]["group"] in ("HR", "IT")
    assert "work_date" in f["trends"]
    assert "days_present" in f["numerics"]
    text = render_facts([f])
    assert "EXACT" in text and "by department" in text


def test_top_n_shares():
    from owl.reports.facts import _read
    df = _read(CSV)
    rows = top_n(df, "status")
    assert rows[0] == {"value": "present", "count": 2, "share": "50.0% (2 of 4)"}
