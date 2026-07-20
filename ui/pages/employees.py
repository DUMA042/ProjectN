import streamlit as st

from ui.lib.queries import search_employees, get_departments, get_statuses
from ui.lib.components import page_header

page_header("Employee Directory", "Search and filter the Nominal Roll")

depts = [""] + get_departments()
statuses = [""] + get_statuses()

col1, col2, col3 = st.columns(3)
with col1:
    search = st.text_input("Search by name or ID", placeholder="Type to search...")
with col2:
    department = st.selectbox("Department", options=depts, format_func=lambda x: "All Departments" if not x else x)
with col3:
    status = st.selectbox("Status", options=statuses, format_func=lambda x: "All Statuses" if not x else x)

page_size = 50

if "emp_page" not in st.session_state:
    st.session_state.emp_page = 1

if search or department or status:
    st.session_state.emp_page = 1

page = st.session_state.emp_page

df, total = search_employees(
    search=search,
    department=department,
    status=status,
    page=page,
    size=page_size,
)

st.caption(f"Showing {len(df)} of {total:,} employees")

if not df.empty:
    st.dataframe(
        df,
        column_config={
            "id_no": "ID No",
            "full_name": "Full Name",
            "sex": "Sex",
            "department_name": "Department",
            "rank_name": "Rank",
            "gl_name": "Grade Level",
            "status_name": "Status",
            "geographical_zone": "Geo Zone",
            "date_of_last_deployment": "Last Deployment",
            "remark": "Remark",
            "phone_number": "Phone",
        },
        width='stretch',
        hide_index=True,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Previous", disabled=(page <= 1), width='stretch'):
            st.session_state.emp_page = max(1, page - 1)
            st.rerun()
    with col_info:
        st.markdown(f"<div style='text-align: center; padding-top: 8px;'>Page {page} of {total_pages}</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("Next →", disabled=(page >= total_pages), width='stretch'):
            st.session_state.emp_page = min(total_pages, page + 1)
            st.rerun()
else:
    st.info("No employees found matching the criteria.")
