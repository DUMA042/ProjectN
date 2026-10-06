"""Build job store + stage machine (pure, no I/O)."""
from __future__ import annotations

import pytest

from owl.reports import jobs


def test_stage_machine_flows_forward():
    job = jobs.create_job(["a", "b"])
    assert job["stage"] == "added"
    assert [f["state"] for f in job["files"]] == ["pending", "pending"]
    for stage in jobs.STAGES[1:]:
        if stage in ("cancelled", "failed", "resolving", "querying", "rendering"):
            continue
        updated = jobs.set_stage(job["id"], stage, f"at {stage}")
        assert updated is not None and updated["stage"] == stage
    assert jobs.get_job(job["id"])["stage"] == "complete"


def test_file_states_and_payload():
    job = jobs.create_job(["a"])
    assert jobs.set_file_state(job["id"], "a", "active")["files"][0]["state"] == "active"
    done = jobs.set_file_state(job["id"], "a", "error", "boom")
    assert done["files"][0] == {"id": "a", "state": "error", "error": "boom"}
    assert jobs.set_payload(job["id"], "needs_hashing", True)["payload"] == {"needs_hashing": True}


def test_cancel_job_is_terminal_and_observable():
    job = jobs.create_job(["a"])
    assert jobs.is_cancelled(job["id"]) is False
    out = jobs.cancel_job(job["id"])
    assert out is not None and out["stage"] == "cancelled"
    assert jobs.is_cancelled(job["id"]) is True
    assert jobs.cancel_job("nope") is None
    assert jobs.is_cancelled("nope") is False


def test_unknown_ids_and_stages_rejected():
    assert jobs.get_job("nope") is None
    assert jobs.set_stage("nope", "added") is None
    job = jobs.create_job(["a"])
    with pytest.raises(ValueError, match="Unknown stage"):
        jobs.set_stage(job["id"], "flying")
    with pytest.raises(ValueError, match="Unknown file state"):
        jobs.set_file_state(job["id"], "a", "flying")
