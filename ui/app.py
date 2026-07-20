import streamlit as st

st.set_page_config(
    page_title="AttendanceN",
    page_icon="🦉",
    layout="wide",
    initial_sidebar_state="expanded",
)

dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")
card_swipe = st.Page("pages/card_swipe.py", title="Card Swipe", icon="💳")
leave = st.Page("pages/leave.py", title="Leave", icon="🏖️")
training = st.Page("pages/training.py", title="Training", icon="🎓")
employees = st.Page("pages/employees.py", title="Employees", icon="👥")
ingestion = st.Page("pages/ingestion.py", title="Upload", icon="📁")

pg = st.navigation([dashboard, card_swipe, leave, training, employees, ingestion])

pg.run()
