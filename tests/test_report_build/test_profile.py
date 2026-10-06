"""CSV profiler unit tests (pure, no I/O)."""
from __future__ import annotations

import pytest

from owl.reports.analysis import grouping_directives, resolve_finals, validate_analysis
from owl.reports.profile import MAX_PACK_CHARS, grouping_dimension, pack_profiles, profile_csv

CSV = (
    "full_name,department,status,work_date,days_present\n"
    "Alice Ama,HR,present,2026-06-02,20\n"
    "Bob Boateng,IT,late,2026-06-03,18\n"
    "Cara Dan,IT,present,2026-06-04,20\n"
)


def test_profile_shape():
    p = profile_csv("people.csv", CSV)
    assert p["file"] == "people.csv" and p["rows"] == 3
    by_name = {c["name"]: c for c in p["columns"]}
    assert by_name["days_present"]["numeric"] is True
    assert by_name["days_present"]["min"] == 18
    assert by_name["status"]["top_values"][0] == {"value": "present", "count": 2}
    assert by_name["work_date"]["date_span"] == {"from": "2026-06-02", "to": "2026-06-04"}
    assert len(p["sample_rows"]) == 3


def test_high_cardinality_columns_have_no_top_values():
    rows = ["token,value"] + [f"ABCDEF{i:04d},{i}" for i in range(30)]
    p = profile_csv("t.csv", "\n".join(rows) + "\n")
    assert p["columns"][0]["top_values"] == []


def test_pack_is_capped():
    big = "a,b\n" + "".join(f"{'x' * 50},{i}\n" for i in range(500))
    pack = pack_profiles([profile_csv("big.csv", big)])
    assert len(pack) <= MAX_PACK_CHARS + len("\n[truncated]")


def test_validate_analysis_accepts_and_normalizes():
    data = {
        "topics": [
            {"name": " Attendance ", "coverage": "has status col", "suggested_focus": "HIGH"},
            {"name": "Leave", "coverage": "", "suggested_focus": "weird"},
            {"name": "  ", "coverage": "x"},
        ],
        "recommended_range": {"min_words": 1000, "max_words": 1500, "reasoning": "why"},
    }
    out = validate_analysis(data)
    assert [t["name"] for t in out["topics"]] == ["Attendance", "Leave"]
    assert out["topics"][0]["suggested_focus"] == "high"
    assert out["topics"][1]["suggested_focus"] == "medium"
    assert out["recommended_range"]["min_words"] == 1000


def test_validate_analysis_rejects():
    with pytest.raises(ValueError, match="no reportable topics"):
        validate_analysis({"topics": [], "recommended_range": {}})
    with pytest.raises(ValueError, match="no word-range"):
        validate_analysis({"topics": [{"name": "A"}]})
    with pytest.raises(ValueError, match="outside sane bounds"):
        validate_analysis({
            "topics": [{"name": "A"}],
            "recommended_range": {"min_words": 10, "max_words": 5},
        })


def test_resolve_finals_prefers_hashed_copies():
    items = [
        {"id": "f1", "classification": "individual", "source": "t"},
        {"id": "h1", "classification": "individual", "source": "hashed:f1"},
        {"id": "f2", "classification": "non_individual", "source": "t"},
    ]
    out = resolve_finals(items, ["f1", "f2"])
    assert [e["id"] for e in out] == ["h1", "f2"]
    # No hashed copy yet -> original is the final.
    out2 = resolve_finals([items[0], items[2]], ["f1", "f2"])
    assert [e["id"] for e in out2] == ["f1", "f2"]


GROUPING_CSV = (
    "full_name,department,grade_level,sex,status,work_date\n"
    "Alice Ama,HR,Level 5,Female,present,2026-06-02\n"
    "Bob Boateng,IT,Level 4,Male,late,2026-06-03\n"
)


def test_grouping_dimension_matching():
    assert grouping_dimension("department") == "department"
    assert grouping_dimension("Department Name") == "department"
    assert grouping_dimension("Grade_Level") == "grade level"
    assert grouping_dimension("SEX") == "sex"
    # Bare day-status "status" must NOT match employment status.
    assert grouping_dimension("status") is None
    assert grouping_dimension("department code") is None
    assert grouping_dimension("notes") is None


def test_profile_flags_grouping_columns():
    p = profile_csv("g.csv", GROUPING_CSV)
    flags = {c["name"]: c.get("grouping") for c in p["columns"]}
    assert flags["department"] == "department"
    assert flags["grade_level"] == "grade level"
    assert flags["sex"] == "sex"
    assert flags.get("status") is None
    pack = pack_profiles([p])
    assert "GROUPING:department" in pack


def test_grouping_directives_mandatory_department():
    profiles = [profile_csv("g.csv", GROUPING_CSV)]
    d = grouping_directives(profiles)
    assert "MANDATORY" in d and "departmental breakdown" in d
    assert "grade level" in d and "sex" in d
    bare = grouping_directives(profile_csv("x.csv", "a,b\n1,2\n") for _ in [0])
    assert bare == "No grouping columns detected: report whole-workforce figures only."
    nodept = grouping_directives([profile_csv("s.csv", "sex,x\nF,1\n")])
    assert "MANDATORY" not in nodept and "sex" in nodept


def test_validate_analysis_dimensions():
    out = validate_analysis({
        "topics": [{"name": "A", "coverage": "c", "suggested_focus": "high",
                    "dimensions": ["department", "  ", 7, "sex"]}],
        "recommended_range": {"min_words": 500, "max_words": 1000},
    })
    assert out["topics"][0]["dimensions"] == ["department", "sex"]
    out2 = validate_analysis({
        "topics": [{"name": "A"}],
        "recommended_range": {"min_words": 500, "max_words": 1000},
    })
    assert out2["topics"][0]["dimensions"] == []


def test_validate_comprehension_accepts_and_rejects():
    from owl.reports.analysis import validate_comprehension

    out = validate_comprehension({
        "files": [{"name": "a.csv", "contains": "attendance", "period": "June", "rows": 100}],
        "join_keys": ["department"],
        "headline_figures": ["rate 83%"],
        "caveats": ["one", "two", "three", "four"],
    })
    assert out["files"][0]["rows"] == 100
    assert out["caveats"] == ["one", "two", "three"]
    import pytest as _pytest
    with _pytest.raises(ValueError, match="named no files"):
        validate_comprehension({"files": []})


def test_finals_signature_changes_with_rows():
    from owl.reports.analysis import finals_signature

    a = [("f.csv", "h\n1\n2\n", "")]
    b = [("f.csv", "h\n1\n", "")]
    assert finals_signature(a) != finals_signature(b)
    assert finals_signature(a) == finals_signature(a)
