import streamlit as st
import plotly.express as px

from ui.lib.queries import (
    get_card_swipe_summary,
    get_card_swipe_by_day,
    get_card_swipe_by_hour,
    get_card_swipe_by_location,
    get_card_swipe_by_month,
    get_recent_card_swipes,
)
from ui.lib.components import page_header

page_header("Card Swipe Analytics", "Attendance swipe patterns and trends")

summary = get_card_swipe_summary()
if summary.empty or summary.iloc[0]["total_swipes"] == 0:
    st.info("No card swipe data available.")
    st.stop()

row = summary.iloc[0]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total Swipes", f"{int(row['total_swipes']):,}")
with k2:
    st.metric("Unique Employees", f"{int(row['unique_employees']):,}")
with k3:
    st.metric("First Swipe", str(row["first_swipe"])[:10] if row["first_swipe"] else "N/A")
with k4:
    st.metric("Last Swipe", str(row["last_swipe"])[:10] if row["last_swipe"] else "N/A")

st.divider()

days = st.slider("Days to show", min_value=7, max_value=90, value=30, step=1)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Swipe Volume by Day")
    day_df = get_card_swipe_by_day(days)
    if not day_df.empty:
        fig = px.line(
            day_df,
            x="swipe_date",
            y="swipe_count",
            markers=True,
            height=400,
        )
        fig.update_traces(line_color="#4C78A8", line_width=2)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Swipe Volume by Hour")
    hour_df = get_card_swipe_by_hour()
    if not hour_df.empty:
        fig = px.bar(
            hour_df,
            x="hour",
            y="swipe_count",
            text_auto=True,
            height=400,
        )
        fig.update_traces(marker_color="#4C78A8")
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(tickmode="linear", dtick=2),
        )
        st.plotly_chart(fig, width='stretch')

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("Swipe Volume by Month")
    month_df = get_card_swipe_by_month()
    if not month_df.empty:
        fig = px.bar(
            month_df,
            x="month",
            y="swipe_count",
            text_auto=True,
            height=400,
        )
        fig.update_traces(marker_color="#2ECC71")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

with col4:
    st.subheader("Top Locations")
    loc_df = get_card_swipe_by_location()
    if not loc_df.empty:
        fig = px.bar(
            loc_df.head(10),
            x="swipe_count",
            y="location_name",
            orientation="h",
            text_auto=True,
            height=400,
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        fig.update_traces(marker_color="#F39C12")
        st.plotly_chart(fig, width='stretch')

st.divider()
st.subheader("Recent Swipe Records")
swipes_df = get_recent_card_swipes(limit=50)
if not swipes_df.empty:
    st.dataframe(
        swipes_df,
        column_config={
            "swipe_id": None,
            "id_no": "ID No",
            "full_name": "Name",
            "swipe_time": "Swipe Time",
            "location": "Location",
        },
        width='stretch',
        hide_index=True,
    )
