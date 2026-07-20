import streamlit as st
import plotly.express as px

from ui.lib.queries import (
    get_training_summary,
    get_training_by_venue,
    get_training_by_consultant,
    get_recent_trainings,
)
from ui.lib.components import page_header

page_header("Training Analytics", "Employee training records and distribution")

summary = get_training_summary()
if summary.empty or summary.iloc[0]["total_records"] == 0:
    st.info("No training data available.")
    st.stop()

row = summary.iloc[0]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total Records", f"{int(row['total_records']):,}")
with k2:
    st.metric("Unique Staff", f"{int(row['unique_staff']):,}")
with k3:
    st.metric("Venues Used", int(row["venues_used"]))
with k4:
    st.metric("Consultants Used", int(row["consultants_used"]))

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Training by Venue")
    venue_df = get_training_by_venue()
    if not venue_df.empty:
        fig = px.bar(
            venue_df,
            x="record_count",
            y="venue_name",
            orientation="h",
            text_auto=True,
            height=400,
        )
        fig.update_traces(marker_color="#3498DB")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Training by Consultant")
    cons_df = get_training_by_consultant()
    if not cons_df.empty:
        fig = px.bar(
            cons_df,
            x="record_count",
            y="consultant_name",
            orientation="h",
            text_auto=True,
            height=400,
        )
        fig.update_traces(marker_color="#9B59B6")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

st.divider()
st.subheader("Recent Training Records")
trainings_df = get_recent_trainings(limit=50)
if not trainings_df.empty:
    st.dataframe(
        trainings_df,
        column_config={
            "training_id": None,
            "id_no": "ID No",
            "full_name": "Name",
            "venue": "Venue",
            "consultant": "Consultant",
            "start_date": "Start Date",
            "end_date": "End Date",
            "title": "Title",
        },
        width='stretch',
        hide_index=True,
    )
