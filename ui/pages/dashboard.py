import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from ui.lib.queries import (
    get_dashboard_summary,
    get_department_distribution,
    get_status_distribution,
    get_recent_ingestions,
    get_leave_breakdown_by_type,
)
from ui.lib.components import page_header

page_header("Dashboard", "Organisational overview at a glance")

summary = get_dashboard_summary()
if summary.empty:
    st.info("No data loaded yet. Upload an Excel file to get started.")
    st.stop()

row = summary.iloc[0]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total Employees", f"{int(row['total_employees']):,}")
with k2:
    st.metric("Active Employees", f"{int(row['active_employees']):,}")
with k3:
    st.metric("Currently on Leave", int(row["staff_on_leave"]))
with k4:
    st.metric("Currently in Training", int(row["staff_in_training"]))

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Employees by Department")
    dept_df = get_department_distribution()
    if not dept_df.empty:
        fig = px.bar(
            dept_df,
            x="employee_count",
            y="department_name",
            orientation="h",
            text_auto=True,
            height=500,
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=0, r=0, t=0, b=0))
        fig.update_traces(marker_color="#4C78A8")
        st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Employee Status")
    status_df = get_status_distribution()
    if not status_df.empty:
        fig = px.pie(
            status_df,
            names="status_name",
            values="employee_count",
            hole=0.4,
            height=500,
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        fig.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(fig, width='stretch')

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("Leave Breakdown by Type")
    leave_df = get_leave_breakdown_by_type()
    if not leave_df.empty:
        fig = px.bar(
            leave_df,
            x="leave_type_name",
            y="total_entries",
            color="leave_type_name",
            text_auto=True,
            height=400,
        )
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

with col4:
    st.subheader("Recent Ingestion Activity")
    ingest_df = get_recent_ingestions(limit=10)
    if not ingest_df.empty:
        status_colors = {
            "completed": "#2ECC71",
            "failed": "#E74C3C",
            "pending": "#F39C12",
            "processing": "#3498DB",
            "quarantined": "#95A5A6",
        }
        ingest_df["color"] = ingest_df["status"].map(status_colors).fillna("#95A5A6")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ingest_df["normalized_filename"].str[:30],
            y=[1] * len(ingest_df),
            marker_color=ingest_df["color"],
            text=ingest_df["status"],
            orientation="v",
            hovertemplate="<b>%{x}</b><br>Status: %{text}<extra></extra>",
        ))
        fig.update_layout(
            height=400,
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=80),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, width='stretch')
