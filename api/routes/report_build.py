"""Build-section pipeline: inspect → hash → (later) AI analysis → Word report.

Stage machine lives in owl.reports.jobs; hashed copies are new manifest
entries (originals untouched). Human-readable errors name the failing file
and what to do next — never raw tracebacks.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.routes.report_inbox import (
    MAX_CSV_BYTES,
    classify_csv,
    count_rows,
    inbox_dir,
    load_manifest_or_500,
    sanitize_stem,
    stored_name,
)
from owl.load.database import get_session
from owl.reports import hashing, jobs
from owl.reports.analysis import (
    analyze_files,
    comprehend_files,
    finals_signature,
    grouping_directives,
    render_understanding,
    resolve_finals,
)

router = APIRouter(tags=["report-build"])

HASH_WARNING_NAMES_AND_IDS = (
    "Important: when both names and IDs are hashed, the generated report "
    "cannot perform or present group-based analysis using employee IDs. "
    "Both names and IDs will be anonymized together, so reporting based "
    "on ID groups will not be possible."
)


class BuildStartRequest(BaseModel):
    file_ids: list[str]


class BuildHashRequest(BaseModel):
    mode: str


class TopicChoice(BaseModel):
    name: str
    include: bool = True
    focus: str = "medium"


class WordRange(BaseModel):
    min_words: int
    max_words: int


class BuildConfigureRequest(BaseModel):
    topics: list[TopicChoice]
    word_range: WordRange


def _entry_or_404(items: list[dict[str, Any]], file_id: str) -> dict[str, Any]:
    entry = next((e for e in items if e.get("id") == file_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found in the Report Builder")
    return entry


@router.post("/reports/build/start")
def build_start(body: BuildStartRequest):
    if not body.file_ids:
        raise HTTPException(status_code=400, detail="Select at least one file to build")
    base = inbox_dir()
    items = load_manifest_or_500(base)
    entries = [_entry_or_404(items, fid) for fid in body.file_ids]
    not_build = [e["display_name"] for e in entries if (e.get("status") or "inbox") != "build"]
    if not_build:
        raise HTTPException(
            status_code=400,
            detail=f"Move these files to the Build section first: {', '.join(not_build)}",
        )
    missing = []
    for e in entries:
        if not (base / e.get("stored_name", "")).exists():
            missing.append(e["display_name"])
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Stored file missing for: {', '.join(missing)}. Re-send them to the Report Builder.",
        )
    job = jobs.create_job([e["id"] for e in entries])
    individual = [e for e in entries if e.get("classification") == "individual"]
    jobs.set_stage(job["id"], "inspected",
                   f"{len(entries)} files inspected, {len(individual)} individual")
    jobs.set_payload(job["id"], "needs_hashing", bool(individual))
    jobs.set_payload(job["id"], "individual_ids", [e["id"] for e in individual])
    return {
        "job_id": job["id"],
        "needs_hashing": bool(individual),
        "individual_files": [
            {"id": e["id"], "display_name": e["display_name"],
             "row_count": e.get("row_count", 0)}
            for e in individual
        ],
        "files": [
            {"id": e["id"], "display_name": e["display_name"],
             "classification": e.get("classification")}
            for e in entries
        ],
        "hash_warning_names_and_ids": HASH_WARNING_NAMES_AND_IDS,
    }


@router.post("/reports/build/{job_id}/hash")
def build_hash(job_id: str, body: BuildHashRequest):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if body.mode not in hashing.HASH_MODES:
        raise HTTPException(
            status_code=400, detail="Hash mode must be 'names_only' or 'names_and_ids'")
    jobs.set_stage(job_id, "hashing", f"Hashing mode: {body.mode}")
    jobs.set_payload(job_id, "hash_mode", body.mode)
    base = inbox_dir()
    items = load_manifest_or_500(base)
    # Hash originals only: entries whose source is "hashed:*" are already
    # hashed output and must never be hashed again (double-hash guard).
    targets = [e for e in (_entry_or_404(items, fid) for fid in job["file_ids"])
               if e.get("classification") == "individual"
               and not str(e.get("source") or "").startswith("hashed:")]
    by_source = {}
    for e in items:
        by_source.setdefault(e.get("source") or "", []).append(e)
    hashed_ids: list[str] = []
    pending: list[tuple[dict[str, Any], str]] = []
    failure: tuple[str, str] | None = None
    try:
        with get_session() as s:
            for e in targets:
                jobs.set_file_state(job_id, e["id"], "active")
                try:
                    text = (base / e["stored_name"]).read_text(encoding="utf-8-sig")
                    new_text, stats = hashing.hash_csv_text(s, text, body.mode)
                except ValueError as exc:
                    jobs.set_file_state(job_id, e["id"], "error", str(exc))
                    failure = (e["display_name"], str(exc))
                    break
                if len(new_text.encode("utf-8")) > MAX_CSV_BYTES:
                    jobs.set_file_state(job_id, e["id"], "error", "Hashed file too large")
                    failure = (e["display_name"], "hashed output exceeds the size limit")
                    break
                stem = sanitize_stem(e["display_name"])
                existing = by_source.get(f"hashed:{e['id']}", [])
                if existing:
                    # Replace the previous hashed copy in place: one hashed
                    # file per original, never duplicates.
                    entry = existing[-1]
                    name = entry["stored_name"]
                    entry.update({
                        "display_name": f"{stem}_hashed.csv",
                        "row_count": count_rows(new_text),
                        "byte_size": len(new_text.encode("utf-8")),
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                        "moved_at": datetime.now(timezone.utc).isoformat(),
                        "classification": classify_csv(new_text),
                        "hash_mode": body.mode,
                        "hash_stats": stats,
                    })
                else:
                    name = stored_name(f"{stem}_hashed")
                    if (base / name).exists():
                        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
                        name = f"{stem}_hashed_{ts}.csv"
                    entry = {
                        "id": uuid.uuid4().hex,
                        "display_name": f"{stem}_hashed.csv",
                        "stored_name": name,
                        "source": f"hashed:{e['id']}",
                        "row_count": count_rows(new_text),
                        "byte_size": len(new_text.encode("utf-8")),
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                        "status": "build",
                        "moved_at": datetime.now(timezone.utc).isoformat(),
                        "classification": classify_csv(new_text),
                        "hash_mode": body.mode,
                        "hash_stats": stats,
                    }
                    items.append(entry)
                pending.append((entry, new_text))
                jobs.set_file_state(job_id, e["id"], "done")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Hashing failed unexpectedly. Your original files are unchanged — please try again.",
        )
    if failure:
        name, reason = failure
        raise HTTPException(
            status_code=400,
            detail=f"Could not hash '{name}': {reason}. "
                   "Check the file has name/ID columns and try again.",
        )
    try:
        from api.routes.report_inbox import save_manifest
        known_ids = {e.get("id") for e in items}
        for entry, new_text in pending:
            (base / entry["stored_name"]).write_text(new_text, encoding="utf-8")
            if entry["id"] not in known_ids:
                items.append(entry)
                known_ids.add(entry["id"])
            hashed_ids.append(entry["id"])
        save_manifest(items, base)
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Could not save the hashed files. Your original files are unchanged — please try again.",
        )
    jobs.set_payload(job_id, "hashed_ids", hashed_ids)
    target_ids = {e["id"] for e in targets}
    for fid in job["file_ids"]:
        if fid not in target_ids:
            jobs.set_file_state(job_id, fid, "done")
    jobs.set_stage(job_id, "validated",
                   f"{len(targets)} files hashed, {len(job['file_ids'])} files validated")
    return {"job_id": job_id, "stage": "validated", "hashed_ids": hashed_ids}


@router.get("/reports/build/jobs/{job_id}")
def build_job_status(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    return job


@router.post("/reports/build/{job_id}/analyze")
def build_analyze(job_id: str):
    """Profile final files and ask the AI for topics + word-range recommendation."""
    from owl.ai import deepseek

    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if job["stage"] not in ("validated", "topics_ready"):
        raise HTTPException(
            status_code=400,
            detail="Hash and validate the files before AI analysis.",
        )
    base = inbox_dir()
    items = load_manifest_or_500(base)
    entries = resolve_finals(items, job["file_ids"])
    if not entries:
        raise HTTPException(status_code=400, detail="No files left to analyze.")
    finals: list[tuple[str, str, str]] = []
    for e in entries:
        try:
            text = (base / e.get("stored_name", "")).read_text(encoding="utf-8-sig")
        except OSError:
            raise HTTPException(
                status_code=400,
                detail=f"Stored file missing for '{e.get('display_name')}'. "
                       "Re-send it to the Report Builder and start a new build.",
            )
        finals.append((e.get("display_name", ""), text, e.get("classification") or ""))
        src = e.get("source") or ""
        jfid = src[len("hashed:"):] if src.startswith("hashed:") else e["id"]
        jobs.set_file_state(job_id, jfid, "active")
    jobs.set_stage(job_id, "sent_to_ai", f"{len(finals)} files sent to AI")
    jobs.set_stage(job_id, "analysis", "AI is reviewing the files")
    try:
        result = analyze_files(finals, job["payload"].get("hash_mode"))
    except deepseek.DeepSeekError as exc:
        jobs.set_stage(job_id, "validated", "AI analysis failed — retry analysis")
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}")
    except ValueError as exc:
        jobs.set_stage(job_id, "validated", "AI reply unreadable — retry analysis")
        raise HTTPException(
            status_code=502,
            detail=f"The AI returned an unusable analysis ({exc}). Please retry.",
        )
    # Comprehension pass: the model must fully understand the data (exact
    # facts, not samples) before any section is ever written.
    from owl.reports.facts import fact_pack, render_facts
    from owl.reports.profile import pack_profiles, profile_csv

    jobs.set_stage(job_id, "analysis", "AI is building a full picture of the data")
    try:
        profiles = [profile_csv(n, t) for n, t, _c in finals]
        fact_text = render_facts([fact_pack(n, t) for n, t, _c in finals])
        understanding = comprehend_files(
            pack_profiles(profiles), fact_text, job["payload"].get("hash_mode"))
    except deepseek.DeepSeekError as exc:
        jobs.set_stage(job_id, "validated", "AI analysis failed — retry analysis")
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}")
    except ValueError as exc:
        jobs.set_stage(job_id, "validated", "AI reply unreadable — retry analysis")
        raise HTTPException(
            status_code=502,
            detail=f"The AI returned an unusable analysis ({exc}). Please retry.",
        )
    jobs.set_payload(job_id, "topics", result["topics"])
    jobs.set_payload(job_id, "recommended_range", result["recommended_range"])
    jobs.set_payload(job_id, "understanding", understanding)
    jobs.set_payload(job_id, "finals_signature", finals_signature(finals))
    for fid in job["file_ids"]:
        jobs.set_file_state(job_id, fid, "done")
    jobs.set_stage(job_id, "topics_ready",
                   f"{len(result['topics'])} topics detected")
    return {"job_id": job_id, "stage": "topics_ready", **result}


@router.post("/reports/build/{job_id}/configure")
def build_configure(job_id: str, body: BuildConfigureRequest):
    """Store the user's topic/focus/word-range choices for generation."""
    from owl.reports.analysis import FOCUS_LEVELS

    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if job["stage"] in ("generating",):
        raise HTTPException(
            status_code=409,
            detail="Report generation is already running. Track its progress instead of starting again.",
        )
    if job["stage"] == "complete":
        pass  # Rebuild path: a new selection rolls the job back to topics_ready below.
    elif job["stage"] != "topics_ready":
        raise HTTPException(
            status_code=400,
            detail=f"Files are at '{job['stage']}' — run AI analysis before choosing report topics.",
        )
    detected = {t.get("name") for t in job["payload"].get("topics", []) if isinstance(t, dict)}
    chosen = []
    for t in body.topics:
        name = t.name.strip()
        if not name or name not in detected:
            raise HTTPException(
                status_code=400, detail=f"Unknown topic '{t.name}'. Choose from the detected topics."
            )
        if t.focus not in FOCUS_LEVELS:
            raise HTTPException(
                status_code=400, detail=f"Focus for '{name}' must be low, medium, or high."
            )
        chosen.append({"name": name, "include": t.include, "focus": t.focus})
    if not any(t["include"] for t in chosen):
        raise HTTPException(status_code=400, detail="Include at least one topic.")
    lo, hi = body.word_range.min_words, body.word_range.max_words
    if lo < 100 or hi < lo or hi > 10000:
        raise HTTPException(status_code=400, detail="Word range is outside sane bounds.")
    jobs.set_payload(job_id, "selection", {"topics": chosen, "word_range": {"min_words": lo, "max_words": hi}})
    if jobs.get_job(job_id)["stage"] == "complete":
        jobs.set_stage(job_id, "topics_ready", "Selection updated — ready to rebuild")
    return {"job_id": job_id, "stage": jobs.get_job(job_id)["stage"], "selection": jobs.get_job(job_id)["payload"]["selection"]}


def _builds_dir(job_id: str):
    return inbox_dir() / "builds" / job_id


@router.post("/reports/build/{job_id}/generate")
def build_generate(job_id: str):
    """Generate all sections, render charts, assemble the Word document.

    Versioned: every call writes HR_Report_{ts}_{slug}.docx (+ meta + charts),
    so rebuilding never overwrites history. Resumable: completed topics are
    persisted per call; retrying the same selection continues where it
    stopped. Cooperative cancel: the loop exits between topics when the job
    is cancelled.
    """
    import json as _json
    import re as _re

    from owl.ai import deepseek
    from owl.reports import generate as gen
    from owl.reports.docx_builder import build_docx
    from owl.reports.profile import pack_profiles, profile_csv

    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if jobs.is_cancelled(job_id):
        raise HTTPException(status_code=409, detail="This build was cancelled.")
    selection = job["payload"].get("selection")
    if not selection:
        raise HTTPException(
            status_code=400, detail="Choose report topics before generating."
        )
    included = [t for t in selection["topics"] if t.get("include")]
    wr = selection["word_range"]
    sel_hash = _json.dumps(selection, sort_keys=True)
    base = inbox_dir()
    items = load_manifest_or_500(base)
    entries = resolve_finals(items, job["file_ids"])
    finals: list[tuple[str, str, str]] = []
    for e in entries:
        try:
            text = (base / e.get("stored_name", "")).read_text(encoding="utf-8-sig")
        except OSError:
            raise HTTPException(
                status_code=400,
                detail=f"Stored file missing for '{e.get('display_name')}'. "
                       "Re-send it to the Report Builder and start a new build.",
            )
        finals.append((e.get("display_name", ""), text, e.get("classification") or ""))
    profiles = [profile_csv(n, t) for n, t, _c in finals]
    pack = pack_profiles(profiles)
    grouping = grouping_directives(profiles)
    # Comprehension gate: refuse to write from stale or missing understanding.
    understanding = job["payload"].get("understanding")
    if not understanding or job["payload"].get("finals_signature") != finals_signature(finals):
        raise HTTPException(
            status_code=400,
            detail="Files changed since analysis — run AI analysis again before generating.",
        )
    from owl.reports.facts import fact_pack, render_facts
    fact_list = [fact_pack(n, t) for n, t, _c in finals]
    fact_text = render_facts(fact_list)
    understanding_text = render_understanding(understanding)
    budgets = gen.word_budgets(included, wr["min_words"], wr["max_words"])
    out_dir = _builds_dir(job_id)

    # Resume: same selection as an unfinished generation reuses its version.
    prev = job["payload"].get("generation") or {}
    if prev.get("selection_hash") == sel_hash and not prev.get("finished"):
        gen_id = prev["gen_id"]
        done = {s["topic"]: (s["markdown"], s.get("kpis", [])) for s in prev.get("sections", [])}
        chart_meta = list(prev.get("charts", []))
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        slug = _re.sub(r"[^\w]+", "-", "-".join(t["name"] for t in included)).strip("-")[:40] or "report"
        gen_id = f"{ts}_{slug}"
        if (out_dir / f"meta_{gen_id}.json").exists():
            # Same-second rebuild: disambiguate, keep both versions.
            gen_id = f"{gen_id}_{datetime.now(timezone.utc).strftime('%f')}"
        done = {}
        chart_meta = []
    charts_dir = out_dir / f"charts_{gen_id}"
    charts_dir.mkdir(parents=True, exist_ok=True)
    filename = f"HR_Report_{gen_id}.docx"

    jobs.set_stage(job_id, "generating", "AI is writing the report")
    sections: list[tuple[str, str]] = [(t, done[t][0]) for t in
                                       [x["name"] for x in included] if t in done]
    section_kpis: list[list[tuple[str, str]]] = [done[t][1] for t in
                                                 [x["name"] for x in included] if t in done]
    try:
        for idx, topic in enumerate(included):
            if jobs.is_cancelled(job_id):
                _save_generation_progress(job_id, gen_id, sel_hash, sections, section_kpis, chart_meta, False)
                raise HTTPException(status_code=409, detail="Build cancelled.")
            if topic["name"] in done:
                continue
            jobs.set_stage(job_id, "generating",
                           f"Writing {topic['name']} ({len(sections) + 1}/{len(included)})")
            # Backend-mandated visuals first: guaranteed comparisons from facts.
            mandated_md = ""
            for s in gen.mandated_visuals(topic["name"], fact_list):
                if len(chart_meta) >= gen.MAX_TOTAL_CHARTS:
                    break
                if any(gen.chart_key(s) == gen.chart_key(c) for c in chart_meta):
                    continue
                fname = f"chart_{len(chart_meta)}.png"
                gen.render_chart(s, charts_dir / fname)
                chart_meta.append({"title": s["title"], "name": fname, "type": s["type"],
                                   "labels": s["labels"], "values": s["values"]})
                mandated_md += f"\n\n![{s['title']}](build-chart:{len(chart_meta) - 1})"
            markdown, specs, kpis = gen.generate_topic_section(
                topic, budgets[topic["name"]], pack,
                job["payload"].get("hash_mode"), grouping,
                facts_text=fact_text, understanding=understanding_text,
            )
            markdown += mandated_md
            for s in gen.dedupe_specs(specs, chart_meta):
                if len(chart_meta) >= gen.MAX_TOTAL_CHARTS:
                    break
                fname = f"chart_{len(chart_meta)}.png"
                gen.render_chart(s, charts_dir / fname)
                chart_meta.append({"title": s["title"], "name": fname, "type": s["type"],
                                   "labels": s["labels"], "values": s["values"]})
                markdown += f"\n\n![{s['title']}](build-chart:{len(chart_meta) - 1})"
            sections.append((topic["name"], markdown))
            section_kpis.append(kpis)
            _save_generation_progress(job_id, gen_id, sel_hash, sections, section_kpis, chart_meta, False)
    except HTTPException:
        raise
    except deepseek.DeepSeekError as exc:
        jobs.set_stage(job_id, "topics_ready", "Report generation failed — retry")
        raise HTTPException(status_code=502, detail=f"Report generation failed: {exc}")
    try:
        docx_path = out_dir / filename
        build_docx(
            title="HR Report",
            intro="Sources: " + ", ".join(n for n, _t, _c in finals),
            sections=sections,
            chart_paths=[(c["title"], charts_dir / c["name"]) for c in chart_meta],
            out_path=docx_path,
            kpi_boxes=section_kpis,
        )
        full_md = "\n\n".join(f"## {h}\n\n{b}" for h, b in sections)
        (out_dir / f"report_{gen_id}.md").write_text(full_md, encoding="utf-8")
    except OSError:
        jobs.set_stage(job_id, "topics_ready", "Report assembly failed — retry")
        raise HTTPException(
            status_code=500,
            detail="Could not assemble the Word document. Please try again.",
        )
    jobs.set_payload(job_id, "report", {
        "gen_id": gen_id,
        "filename": filename,
        "charts": chart_meta,
        "word_range": wr,
    })
    (out_dir / f"meta_{gen_id}.json").write_text(_json.dumps({
        "job_id": job_id,
        "gen_id": gen_id,
        "filename": filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "topics": included,
        "word_range": wr,
        "hash_mode": job["payload"].get("hash_mode"),
        "sources": [n for n, _t, _c in finals],
    }, indent=2), encoding="utf-8")
    # Legacy single-file pointers (kept for older clients): latest wins.
    (out_dir / "meta.json").write_text(_json.dumps({"latest_gen_id": gen_id}), encoding="utf-8")
    _save_generation_progress(job_id, gen_id, sel_hash, sections, section_kpis, chart_meta, True)
    jobs.set_stage(job_id, "complete", "Report complete")
    return {"job_id": job_id, "stage": "complete", "gen_id": gen_id, "charts": chart_meta}


def _save_generation_progress(
    job_id: str, gen_id: str, sel_hash: str,
    sections: list[tuple[str, str]], section_kpis: list[list[tuple[str, str]]],
    chart_meta: list[dict[str, str]],
    finished: bool,
) -> None:
    jobs.set_payload(job_id, "generation", {
        "gen_id": gen_id,
        "selection_hash": sel_hash,
        "sections": [{"topic": t, "markdown": m, "kpis": k}
                     for (t, m), k in zip(sections, section_kpis)],
        "charts": chart_meta,
        "finished": finished,
    })


def _latest_gen(job_id: str) -> tuple[str, Path] | None:
    """Newest versioned generation for a job: (gen_id, job dir).

    Falls back to the pre-versioning layout ("legacy") so reports built
    before versioning stay visible and downloadable.
    """
    out_dir = _builds_dir(Path(job_id).name)
    if not out_dir.exists():
        return None
    metas = sorted(out_dir.glob("meta_*.json"))
    if metas:
        return metas[-1].stem[len("meta_"):], out_dir
    if (out_dir / "HR_Report.docx").exists():
        return "legacy", out_dir
    return None


def _gen_paths(out_dir: Path, gen_id: str) -> tuple[str, Path, Path, Path]:
    """(docx filename, docx path, markdown path, charts dir) for a version."""
    if gen_id == "legacy":
        return ("HR_Report.docx", out_dir / "HR_Report.docx",
                out_dir / "report.md", out_dir / "charts")
    import json as _json

    filename = f"HR_Report_{gen_id}.docx"
    try:
        meta = _json.loads((out_dir / f"meta_{gen_id}.json").read_text(encoding="utf-8"))
        if isinstance(meta, dict) and meta.get("filename"):
            filename = meta["filename"]
    except (ValueError, OSError):
        pass
    return (filename, out_dir / filename,
            out_dir / f"report_{gen_id}.md", out_dir / f"charts_{gen_id}")


@router.post("/reports/build/{job_id}/cancel")
def build_cancel(job_id: str):
    """Cancel a running build and clean up everything it created.

    Originals are never touched. Removes this job's hashed copies (manifest
    entries + files) and any partial builds/{job} output. In-flight loops
    observe the cancelled flag and stop between topics.
    """
    import shutil

    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if job["stage"] == "complete":
        raise HTTPException(
            status_code=400,
            detail="This report is already complete — delete it from Generated reports instead.",
        )
    cancelled = jobs.cancel_job(job_id)
    removed = 0
    try:
        base = inbox_dir()
        items = load_manifest_or_500(base)
        doomed = {hid for hid in (job["payload"].get("hashed_ids") or [])}
        kept = []
        for e in items:
            if e.get("id") in doomed:
                try:
                    (base / e.get("stored_name", "")).unlink(missing_ok=True)
                except OSError:
                    pass
                removed += 1
            else:
                kept.append(e)
        if removed:
            from api.routes.report_inbox import save_manifest
            save_manifest(kept, base)
        shutil.rmtree(_builds_dir(job_id), ignore_errors=True)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Build cancelled, but some created files may remain. Delete them from the Inbox if needed.",
        )
    return {"job_id": job_id, "cancelled": True, "removed_hashed": removed,
            "stage": (cancelled or {}).get("stage", "cancelled")}


@router.get("/reports/build/{job_id}/report")
def build_report_view(job_id: str):
    """Preview payload: markdown + chart URLs + download URL (latest version)."""
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Build job not found")
    if job["stage"] != "complete":
        raise HTTPException(status_code=400, detail="The report is not ready yet.")
    latest = _latest_gen(job_id)
    if not latest:
        raise HTTPException(status_code=500, detail="Report file missing. Generate it again.")
    gen_id, out_dir = latest
    try:
        _fname, _docx, md_path, _charts = _gen_paths(out_dir, gen_id)
        markdown = md_path.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail="Report file missing. Generate it again.")
    charts = job["payload"].get("report", {}).get("charts", [])
    for c in charts:
        c["url"] = f"/api/reports/build/{job_id}/chart/{c['name']}"
    report = job["payload"].get("report", {}) or {}
    return {
        "job_id": job_id,
        "gen_id": gen_id,
        "filename": report.get("filename", f"HR_Report_{gen_id}.docx"),
        "markdown": markdown,
        "charts": charts,
        "download_url": f"/api/reports/build/{job_id}/download",
    }


@router.get("/reports/build/{job_id}/download")
def build_report_download(job_id: str):
    job = jobs.get_job(job_id)
    if not job or job["stage"] != "complete":
        raise HTTPException(status_code=404, detail="Report not found")
    latest = _latest_gen(job_id)
    if not latest:
        raise HTTPException(status_code=404, detail="Report file missing")
    gen_id, out_dir = latest
    filename, path, _md, _charts = _gen_paths(out_dir, gen_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")
    return FileResponse(str(path),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=filename)


@router.get("/reports/build/{job_id}/chart/{name}")
def build_report_chart(job_id: str, name: str):
    latest = _latest_gen(job_id)
    if not latest:
        raise HTTPException(status_code=404, detail="Chart not found")
    gen_id, out_dir = latest
    _fname, _docx, _md, charts_dir = _gen_paths(out_dir, gen_id)
    path = charts_dir / Path(name).name
    if not path.exists() or path.suffix.lower() != ".png":
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(str(path), media_type="image/png")


def _parse_entry_id(entry_id: str) -> tuple[str, str] | None:
    """'job:gen' -> (job, gen); None when malformed."""
    safe = Path(entry_id).name
    if ":" not in safe:
        return None
    job_id, gen_id = safe.split(":", 1)
    if not job_id or not gen_id or "/" in gen_id or "\\" in gen_id:
        return None
    return job_id, gen_id


@router.get("/reports/builds")
def builds_list():
    """All stored report versions (survives reloads/restarts): newest first."""
    import json as _json

    root = inbox_dir() / "builds"
    out: list[dict[str, Any]] = []
    if root.exists():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            metas = sorted(child.glob("meta_*.json"), reverse=True)
            if not metas and (child / "HR_Report.docx").exists():
                # Pre-versioning layout: surface it as one "legacy" entry.
                legacy: dict[str, Any] = {}
                try:
                    legacy = _json.loads((child / "meta.json").read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    pass
                if not isinstance(legacy, dict):
                    legacy = {}
                topics = legacy.get("topics") if isinstance(legacy.get("topics"), list) else []
                out.append({
                    "entry_id": f"{child.name}:legacy",
                    "job_id": child.name,
                    "filename": "HR_Report.docx",
                    "created_at": legacy.get("created_at", ""),
                    "topics": [t.get("name", "") for t in topics if isinstance(t, dict)],
                    "word_range": legacy.get("word_range"),
                    "download_url": f"/api/reports/builds/{child.name}:legacy/download",
                })
                continue
            for meta_path in metas:
                gen_id = meta_path.stem[len("meta_"):]
                try:
                    meta = _json.loads(meta_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                if not isinstance(meta, dict):
                    continue
                filename = meta.get("filename", f"HR_Report_{gen_id}.docx")
                if not (child / filename).exists():
                    continue
                topics = meta.get("topics") if isinstance(meta.get("topics"), list) else []
                out.append({
                    "entry_id": f"{child.name}:{gen_id}",
                    "job_id": child.name,
                    "filename": filename,
                    "created_at": meta.get("created_at", ""),
                    "topics": [t.get("name", "") for t in topics if isinstance(t, dict)],
                    "word_range": meta.get("word_range"),
                    "download_url": f"/api/reports/builds/{child.name}:{gen_id}/download",
                })
    out.sort(key=lambda e: (e["created_at"], e["entry_id"]), reverse=True)
    return {"reports": out}


@router.get("/reports/builds/{entry_id}/download")
def builds_entry_download(entry_id: str):
    parsed = _parse_entry_id(entry_id)
    if not parsed:
        raise HTTPException(status_code=404, detail="Report not found")
    job_id, gen_id = parsed
    out_dir = _builds_dir(job_id)
    filename, path, _md, _charts = _gen_paths(out_dir, gen_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")
    return FileResponse(str(path),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=filename)


@router.delete("/reports/builds/{entry_id}")
def builds_delete(entry_id: str):
    """Delete one stored report version (docx + meta + its charts)."""
    parsed = _parse_entry_id(entry_id)
    if not parsed:
        raise HTTPException(status_code=404, detail="Report not found")
    job_id, gen_id = parsed
    out_dir = _builds_dir(job_id)
    import shutil

    if gen_id == "legacy":
        targets = [out_dir / "HR_Report.docx", out_dir / "report.md",
                   out_dir / "meta.json", out_dir / "charts"]
    else:
        filename, _docx, _md, _charts = _gen_paths(out_dir, gen_id)
        targets = [out_dir / filename, out_dir / f"report_{gen_id}.md",
                   out_dir / f"meta_{gen_id}.json", out_dir / f"charts_{gen_id}"]
    found = False
    for p in targets:
        try:
            if p.is_dir():
                shutil.rmtree(p)
                found = True
            elif p.exists():
                p.unlink()
                found = True
        except OSError:
            pass
    if not found:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": entry_id}
