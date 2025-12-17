# screens/edge_tutor.py
import streamlit as st
import os
from components.edge_chat import show_edge_chat


def _perform_reset(clear_chats: bool = True):
    """Helper to perform reset with optional chat clearing."""
    # Preserve reset flags
    reset_performed = st.session_state.get("_reset_performed", False)
    reset_backup = st.session_state.get("_reset_backup")
    
    keys_to_clear = [
        "analysis_result",
        "saved_files",
        "uploaded_files",
        "analysis_start_time",
        "selected_topic",
        "selected_edge",
    ]
    
    if clear_chats:
        # Clear chat histories
        for key in list(st.session_state.keys()):
            if key.startswith("topic_chat_") or key.startswith("edge_chat_") or key == "dashboard_chat_messages":
                del st.session_state[key]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Restore reset flags if they were set
    if reset_performed:
        st.session_state["_reset_performed"] = True
    if reset_backup is not None:
        st.session_state["_reset_backup"] = reset_backup
    
    # Go back to welcome page
    st.session_state["page"] = "welcome"
    st.rerun()


def show_edge_tutor():
    """Page for explaining connections between two topics."""
    edge_info = st.session_state.get("selected_edge")
    
    if edge_info is None:
        st.warning("No edge selected. Please select a topic connection from the concept map.")
        if st.button("Go to concept map"):
            st.session_state["page"] = "concept_map"
            st.rerun()
        return
    
    # Check if we need to show undo option
    if st.session_state.get("_reset_performed", False):
        st.warning("⚠️ Reset performed. You can undo this action.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Reset", key="confirm_reset"):
                st.session_state["_reset_performed"] = False
                if "_reset_backup" in st.session_state:
                    del st.session_state["_reset_backup"]
                st.rerun()
        with col2:
            if st.button("↩️ Undo Reset", key="undo_reset"):
                # Restore from backup
                if "_reset_backup" in st.session_state:
                    backup = st.session_state["_reset_backup"]
                    for key, value in backup.items():
                        st.session_state[key] = value
                    del st.session_state["_reset_backup"]
                st.session_state["_reset_performed"] = False
                st.rerun()
        return
    
    topic_a = edge_info.get("topic_a", "Topic A")
    topic_b = edge_info.get("topic_b", "Topic B")
    topic_a_label = edge_info.get("topic_a_label", topic_a)
    topic_b_label = edge_info.get("topic_b_label", topic_b)
    
    # --------- CSS ----------
    st.markdown(
        """
    <style>
        #MainMenu, header, footer {visibility: hidden;}

        .main .block-container {
            max-width: 900px !important;
            padding-top: 3.5rem !important;
            padding-bottom: 2.5rem !important;
            margin: 0 auto !important;
        }

        .edge-title-main {
            text-align: left;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1a0d2e;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 0.25rem;
            letter-spacing: -0.5px;
        }

        .edge-subtitle-main {
            text-align: left;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #6b7280;
            font-size: 15px;
            margin-bottom: 1.5rem;
        }

        /* Purple buttons - all buttons visible */
        div.stButton > button {
            background-color: #8b5cf6 !important;
            color: white !important;
            border-radius: 999px !important;
            border: none !important;
            font-weight: 500 !important;
            padding: 10px 26px !important;
            font-size: 15px !important;
            visibility: visible !important;
            display: block !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
    
    # --------- PAGE CONTENT ----------
    left, centre, right = st.columns([1, 2, 1])
    with centre:
        st.markdown(
            f"<h1 class='edge-title-main'>{topic_a_label} ↔ {topic_b_label}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p class='edge-subtitle-main'>Understanding how these topics connect</p>",
            unsafe_allow_html=True,
        )
        
        # Signifier: What can user do here?
        st.info("💡 **What you can do:** Ask questions about how these topics relate, or request a deeper explanation of their connection.")
        
        st.write("")
        
        # Edge chat
        show_edge_chat(topic_a_label, topic_b_label, topic_a, topic_b)
        
        st.write("")
        
        # Navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to concept map"):
                st.session_state["page"] = "concept_map"
                st.rerun()
        with col2:
            if st.button("🔄 New Upload"):
                # Save current session before resetting (only if it's a new session, not already saved)
                if "analysis_result" in st.session_state:
                    chats = {}
                    for key in list(st.session_state.keys()):
                        if key.startswith("topic_chat_") or key.startswith("edge_chat_") or key == "dashboard_chat_messages":
                            chats[key] = st.session_state[key]
                    
                    saved_files = st.session_state.get("saved_files", [])
                    if saved_files:
                        file_names = [os.path.basename(f) for f in saved_files[:3]]
                        session_name = ", ".join(file_names)
                        if len(saved_files) > 3:
                            session_name += f" +{len(saved_files) - 3} more"
                    else:
                        session_name = "Previous Session"
                    
                    # Initialize previous_sessions if not exists
                    if "previous_sessions" not in st.session_state:
                        st.session_state["previous_sessions"] = []
                    
                    # Check if this session already exists (by comparing saved_files)
                    session_exists = False
                    current_saved_files = st.session_state.get("saved_files", [])
                    for existing_session in st.session_state["previous_sessions"]:
                        existing_files = existing_session.get("saved_files", [])
                        # Compare file lists
                        if len(current_saved_files) == len(existing_files):
                            if all(f1 == f2 for f1, f2 in zip(sorted(current_saved_files), sorted(existing_files))):
                                session_exists = True
                                break
                    
                    # Only save if it's a new session (not already in previous_sessions)
                    if not session_exists:
                        session_data = {
                            "name": session_name,
                            "analysis_result": st.session_state.get("analysis_result"),
                            "saved_files": st.session_state.get("saved_files", []),
                            "uploaded_files": st.session_state.get("uploaded_files"),
                            "chats": chats,
                        }
                        
                        # Add to previous sessions (keep last 5)
                        st.session_state["previous_sessions"].insert(0, session_data)
                        if len(st.session_state["previous_sessions"]) > 5:
                            st.session_state["previous_sessions"] = st.session_state["previous_sessions"][:5]
                
                # Reset and go to welcome page
                _perform_reset(clear_chats=True)

