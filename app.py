# app.py
import streamlit as st

from screens.welcome import show_welcome
from screens.analyzing import show_analyzing
from screens.dashboard import show_dashboard
from screens.concept_map import show_concept_map
from screens.topic_tutor import show_topic_tutor
from screens.edge_tutor import show_edge_tutor

# --------- PAGE CONFIG (only here!) ----------
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------- SESSION STATE ----------
if "page" not in st.session_state:
    st.session_state["page"] = "welcome"   # "welcome" | "analyzing" | "dashboard" | "concept_map" | "topic_tutor" | "edge_tutor"

# --------- ROUTER ----------
page = st.session_state["page"]

if page == "welcome":
    show_welcome()
elif page == "analyzing":
    show_analyzing()
elif page == "dashboard":
    show_dashboard()
elif page == "concept_map":
    show_concept_map()
elif page == "topic_tutor":
    show_topic_tutor()
elif page == "edge_tutor":
    show_edge_tutor()
else:
    st.session_state["page"] = "welcome"
    show_welcome()
