import time
import shutil
from pathlib import Path

import streamlit as st
from sqlalchemy import select

from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.ingest.manager import IngestionManager, INBOX_DIR
from owl.ingest.worker import IngestionWorker
from ui.lib.components import page_header, status_badge
from ui.lib.queries import get_recent_ingestions

page_header("File Upload & Ingestion", "Upload Excel files and process them through the pipeline")

uploaded_file = st.file_uploader(
    "Choose an Excel file (.xlsx)",
    type=["xlsx"],
    help="Drag and drop or browse to select a file",
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    dest = INBOX_DIR / file_name
    INBOX_DIR.mkdir(exist_ok=True)

    with st.status("Processing file...", expanded=True) as status:
        st.write("📁 **File received** — saved to inbox")
        with open(dest, "wb") as fh:
            fh.write(file_bytes)

        manager = IngestionManager()

        st.write("🔍 **Classifying file type...**")
        time.sleep(0.5)

        try:
            manager.run_once()
        except Exception as exc:
            st.error(f"Classification failed: {exc}")
            st.stop()

        status.update(label="File classified and routed", state="running")

        pending = None
        with get_session() as session:
            pending = session.execute(
                select(FileIngestionMeta).where(
                    FileIngestionMeta.original_filename == file_name
                ).order_by(FileIngestionMeta.created_at.desc())
            ).scalars().first()

            if pending is None:
                pending = session.execute(
                    select(FileIngestionMeta).order_by(FileIngestionMeta.created_at.desc())
                ).scalars().first()

        if pending:
            st.write(f"📂 **Routed** to `nest/` as `{pending.normalized_filename}`")
            st.write(f"🏷️ **Type:** {pending.report_type} | **Status:** {status_badge(pending.status)} {pending.status}")
        else:
            st.write("📂 **Routed** to `nest/`")

        st.write("⚙️ **Processing data...**")
        worker = IngestionWorker()

        try:
            worker.run_once()
        except Exception as exc:
            st.error(f"Processing failed: {exc}")

        status.update(label="Polling for completion...", state="running")

        record_id = pending.id if pending else None
        if record_id:
            for attempt in range(30):
                time.sleep(1)
                with get_session() as session:
                    record = session.get(FileIngestionMeta, record_id)
                if record is None:
                    continue
                current_status = record.status
                if current_status == "completed":
                    st.write(f"✅ **Completed!** — {record.normalized_filename} processed successfully")
                    status.update(label="Complete", state="complete", expanded=False)
                    break
                elif current_status == "failed":
                    err = record.error_context or {}
                    st.error(f"❌ Processing failed: {err}")
                    status.update(label="Failed", state="error")
                    break
                else:
                    st.write(f"⏳ Status: {current_status}...")
            else:
                st.warning("⏰ Timed out waiting for processing to complete.")
        else:
            st.info("Processing initiated — check history below for status.")

    st.balloons()

st.divider()
st.subheader("Ingestion History")
ingest_df = get_recent_ingestions(limit=20)

if not ingest_df.empty:
    col_map = {
        "normalized_filename": "Filename",
        "report_type": "Type",
        "status": "Status",
        "created_at": "Uploaded",
        "processed_at": "Processed",
    }
    display_df = ingest_df[list(col_map.keys())].rename(columns=col_map)
    display_df["Status"] = display_df["Status"].apply(
        lambda s: f"{status_badge(s)} {s}"
    )

    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
    )

    with get_session() as session:
        failed_records = session.execute(
            select(FileIngestionMeta).where(FileIngestionMeta.status == "failed")
        ).scalars().all()

    if failed_records:
        st.subheader("Failed Records")
        st.warning(f"{len(failed_records)} record(s) need reprocessing.")
        if st.button("🔄 Reprocess Failed Records"):
            with get_session() as session:
                for rec in failed_records:
                    rec = session.merge(rec)
                    session.delete(rec)
                session.commit()
            st.success("Failed records cleared. Move the files back to inbox/ and upload again.")
            st.rerun()
else:
    st.info("No ingestion history yet.")
