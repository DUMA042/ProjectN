"""Individual attendance reports — deterministic per-employee Word documents.

Flow: select location/departments/individuals + date range -> roster query ->
day cells (shared rule classifier) -> parameterized Word builder (cover,
how-to-read, department bands, per-employee grid + summary). No AI and no
hashing anywhere: every value is computed and nothing leaves this system,
so real names render directly.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from owl.load.database import get_session
from owl.reports import individual as ind
from owl.reports import jobs
from owl.reports.individual import file_stem, period_label
from owl.reports.individual_docx import build_individual_docx

router = APIRouter(tags=["individual-reports"])


def _base_dir() -> Path:
    from owl.config import settings

    d = Path(str(settings.report_inbox_dir)) / "individual"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _job_dir(job_id: str) -> Path:
    return _base_dir() / Path(job_id).name


class IndividualBuildRequest(BaseModel):
    location: str = ""
    departments: list[str] = []
    employee_ids: list[str] = []
    search: str = ""
    start_date: str
    end_date: str


class _BuildFail(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _run_individual_build(jid: str, body: IndividualBuildRequest) -> None:
    """Worker-thread pipeline: roster -> days -> docx (no AI, no hashing)."""
    try:
        sd = date.fromisoformat(body.start_date)
        ed = date.fromisoformat(body.end_date)
    except ValueError:
        jobs.set_stage(jid, "failed", "Invalid dates")
        return
    dates = [sd + timedelta(days=i) for i in range((ed - sd).days + 1)]
    try:
        # Rule settings first: grid columns are working days + holidays only.
        ctx = ind.load_context()
        grid_dates = ind.report_dates(sd, ed, ctx.working_dows, ctx.holiday_set)
        if not grid_dates:
            jobs.set_stage(jid, "failed", "No workdays in this range")
            return
        jobs.set_stage(jid, "resolving", "Finding matching employees")
        with get_session() as s:
            roster = ind.resolve_roster(
                s, body.location, body.departments, body.employee_ids, body.search)
        if not roster:
            jobs.set_stage(jid, "failed", "No employees matched the selection")
            return
        # Track per-employee progress from here on.
        jobs.add_files(jid, [e["id_no"] for e in roster])
        jobs.set_stage(jid, "querying", f"Loading {len(roster)} employees × {len(dates)} days")
        with get_session() as s:
            day_data = ind.load_day_data(s, [e["id_no"] for e in roster], sd, ed)
        reports = []
        for i, emp in enumerate(roster):
            if jobs.is_cancelled(jid):
                return
            jobs.set_file_state(jid, emp["id_no"], "active")
            try:
                reports.append(ind.build_employee_report(emp, day_data[emp["id_no"]], grid_dates, ctx))
            except Exception as exc:
                jobs.set_file_state(jid, emp["id_no"], "error", str(exc))
                raise _BuildFail(500, f"Could not compute days for '{emp.get('full_name')}'.")
            jobs.set_file_state(jid, emp["id_no"], "done")
            if (i + 1) % 50 == 0:
                jobs.set_stage(jid, "querying", f"Computed {i + 1}/{len(roster)} employees")
        # No hashing: processed data never leaves this system (no AI, no
        # third party), so real names render directly.
        for rep in reports:
            rep["employee"]["display_name"] = rep["employee"]["full_name"]
        if jobs.is_cancelled(jid):
            return
        jobs.set_stage(jid, "rendering", "Writing the Word document")
        try:
            dept_groups: dict[str, list[dict]] = {}
            for rep in reports:
                dept_groups.setdefault(rep["employee"]["department"], []).append(rep)
            per = period_label(sd, ed)
            loc_label = body.location or "All locations"
            depts = sorted({e["department"] for e in roster})
            meta_line = (
                f"{len(roster)} employees  |  {loc_label}  |  "
                f"{len(depts)} department{'s' if len(depts) != 1 else ''}  |  "
                f"{len(dates)} workdays"            )
            out_dir = _job_dir(jid)
            out_path = out_dir / f"{file_stem(body.location, sd, ed)}.docx"
            build_individual_docx(loc_label, per, meta_line,
                                  sorted(dept_groups.items()), grid_dates, out_path)
            (out_dir / "meta.json").write_text(json.dumps({
                "job_id": jid,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "location": loc_label,
                "departments": depts,
                "headcount": len(roster),
                "period": per,
                "start_date": sd.isoformat(),
                "end_date": ed.isoformat(),
                "filename": out_path.name,
            }, indent=2), encoding="utf-8")
        except OSError:
            raise _BuildFail(500, "Could not write the Word document.")
        jobs.set_payload(jid, "result", {
            "headcount": len(roster),
            "filename": out_path.name,
            "download_url": f"/api/individual-reports/{jid}/download",
        })
        jobs.set_stage(jid, "complete", f"Report complete — {len(roster)} employees")
    except _BuildFail as fail:
        jobs.set_stage(jid, "failed", fail.detail)
    except Exception as exc:
        import logging as _logging

        _logging.getLogger("owl.reports.individual").exception(
            "individual build %s failed", jid)
        jobs.set_stage(jid, "failed", "The report build failed unexpectedly.")


@router.post("/individual-reports/build")
def individual_build(body: IndividualBuildRequest):
    import threading

    try:
        sd = date.fromisoformat(body.start_date)
        ed = date.fromisoformat(body.end_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Dates must be YYYY-MM-DD.")
    if sd > ed:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date.")
    if (ed - sd).days + 1 > ind.MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Date range is too wide (max {ind.MAX_RANGE_DAYS} days). Split it into smaller reports.",
        )
    # Return immediately: the worker thread streams progress into the job.
    job = jobs.create_job([])
    jid = job["id"]
    snapshot = IndividualBuildRequest(**body.model_dump())
    worker = threading.Thread(target=_run_individual_build, args=(jid, snapshot), daemon=True)
    worker.start()
    return {"job_id": jid, "stage": "resolving"}


@router.post("/individual-reports/{job_id}/cancel")
def individual_cancel(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if job["stage"] == "complete":
        raise HTTPException(
            status_code=400,
            detail="This report is already complete — delete it from the list instead.")
    cancelled = jobs.cancel_job(job_id)
    shutil.rmtree(_job_dir(job_id), ignore_errors=True)
    return {"job_id": job_id, "cancelled": True,
            "stage": (cancelled or {}).get("stage", "cancelled")}


@router.get("/individual-reports")
def individual_list():
    """Finished individual reports (filesystem-backed): newest first."""
    import json as _json

    root = _base_dir()
    out: list[dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            meta = _json.loads((child / "meta.json").read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(meta, dict) or not (child / meta.get("filename", "")).exists():
            continue
        out.append({
            "job_id": child.name,
            "filename": meta.get("filename", ""),
            "created_at": meta.get("created_at", ""),
            "location": meta.get("location", ""),
            "departments": meta.get("departments", []),
            "headcount": meta.get("headcount", 0),
            "period": meta.get("period", ""),
            "download_url": f"/api/individual-reports/{child.name}/download",
        })
    out.sort(key=lambda e: (e["created_at"], e["job_id"]), reverse=True)
    return {"reports": out}


@router.get("/individual-reports/{job_id}/download")
def individual_download(job_id: str):
    out_dir = _job_dir(job_id)
    import json as _json

    try:
        meta = _json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
        filename = meta.get("filename", "")
    except (ValueError, OSError):
        filename = ""
    path = out_dir / Path(filename).name if filename else None
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.name)


@router.delete("/individual-reports/{job_id}")
def individual_delete(job_id: str):
    target = _job_dir(job_id)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        shutil.rmtree(target)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not delete the report.")
    return {"deleted": target.name}
