import streamlit as st
import plotly.express as px

from ui.lib.queries import (
    get_leave_summary,
    get_leave_breakdown_by_type,
    get_leave_by_month,
    get_recent_leaves,
)
from ui.lib.components import page_header

page_header("Leave Analytics", "Leave records, types, and trends")

summary = get_leave_summary()
if summary.empty or summary.iloc[0]["total_records"] == 0:
    st.info("No leave data available.")
    st.stop()

row = summary.iloc[0]

k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Total Leave Records", f"{int(row['total_records']):,}")
with k2:
    st.metric("Unique Staff", f"{int(row['unique_staff']):,}")
with k3:
    st.metric("Leave Types Used", int(row["leave_types_used"]))

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Leave Breakdown by Type")
    type_df = get_leave_breakdown_by_type()
    if not type_df.empty:
        fig = px.bar(
            type_df,
            x="leave_type_name",
            y="total_entries",
            color="leave_type_name",
            text_auto=True,
            height=450,
        )
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Leave by Type (Unique Staff)")
    if not type_df.empty:
        fig = px.pie(
            type_df,
            names="leave_type_name",
            values="unique_staff",
            hole=0.4,
            height=450,
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        fig.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(fig, width='stretch')

st.divider()

st.subheader("Leave Records Over Time")
month_df = get_leave_by_month()
if not month_df.empty:
    fig = px.line(
        month_df,
        x="month",
        y="record_count",
        markers=True,
        height=400,
    )
    fig.update_traces(line_color="#E74C3C", line_width=2)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, width='stretch')

st.divider()
st.subheader("Recent Leave Records")
leaves_df = get_recent_leaves(limit=50)
if not leaves_df.empty:
    st.dataframe(
        leaves_df,
        column_config={
            "record_id": None,
            "id_no": "ID No",
            "full_name": "Name",
            "leave_type_name": "Leave Type",
            "start_date": "Start Date",
            "end_date": "End Date",
        },
        width='stretch',
        hide_index=True,
    )
