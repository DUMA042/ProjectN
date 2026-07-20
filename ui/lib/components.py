import streamlit as st


def kpi_card(label, value, delta=None, help_text=None):
    cols = st.columns([1, 4, 1])
    with cols[1]:
        st.metric(label=label, value=value, delta=delta, help=help_text)


def status_badge(status):
    badges = {
        "completed": "✅",
        "processing": "🔄",
        "pending": "⏳",
        "failed": "❌",
        "quarantined": "⚠️",
    }
    return badges.get(status.lower(), "❓")


def page_header(title, subtitle=None):
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()
