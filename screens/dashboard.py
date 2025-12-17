# screens/dashboard.py
import streamlit as st
import os
from components.chat import show_dashboard_chat, handle_dashboard_chat_input


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


def show_dashboard():
    # --------- CSS (your original design) ----------
    st.markdown(
        """
    <style>
        #MainMenu, header, footer {visibility: hidden;}

        .main .block-container {
            max-width: 1400px !important;
            padding-top: 3.5rem !important;
            padding-bottom: 2.5rem !important;
            margin: 0 auto !important;
        }

        .dashboard-title {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1a0d2e;
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }

        .dashboard-subtitle {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #4b5563;
            font-size: 16px;
            margin-bottom: 2rem;
        }

        .topic-card {
            background: #ffffff;
            border-radius: 18px;
            padding: 18px 22px;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 14px;
            margin-bottom: 14px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .dot {
            width: 12px;
            height: 12px;
            border-radius: 999px;
        }

        .dot-red { background-color: #f97373; }
        .dot-yellow { background-color: #facc15; }
        .dot-green { background-color: #22c55e; }

        .topic-main {
            display: flex;
            flex-direction: column;
        }

        .topic-title {
            font-size: 16px;
            font-weight: 600;
            color: #111827;
        }

        .topic-subtitle {
            font-size: 14px;
            color: #6b7280;
            margin-top: 2px;
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
        
        /* Hand-drawn style buttons */
        .hand-drawn-btn {
            background: white !important;
            border: 3px dashed #8b5cf6 !important;
            border-radius: 15px !important;
            padding: 20px 30px !important;
            font-family: 'Comic Sans MS', 'Marker Felt', 'Comic Neue', cursive !important;
            font-size: 18px !important;
            color: #6b21a8 !important;
            font-weight: 600 !important;
            text-align: center !important;
            cursor: pointer !important;
            position: relative !important;
            transform: rotate(-1deg) !important;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1) !important;
            transition: all 0.2s !important;
        }
        
        .hand-drawn-btn:hover {
            transform: rotate(0.5deg) scale(1.02) !important;
            box-shadow: 3px 5px 12px rgba(0,0,0,0.15) !important;
        }
        
        .hand-drawn-btn::before {
            content: '';
            position: absolute;
            top: -5px;
            left: 20%;
            width: 60%;
            height: 2px;
            background: #8b5cf6;
            transform: rotate(-2deg);
            opacity: 0.6;
        }
        
        .hand-drawn-container {
            position: relative;
            padding: 15px;
        }
        
        .hand-drawn-line {
            position: absolute;
            border: 2px solid #8b5cf6;
            border-radius: 50%;
            opacity: 0.4;
        }
        
        .line-1 {
            top: 10px;
            left: 15px;
            width: 80px;
            height: 40px;
            transform: rotate(-15deg);
        }
        
        .line-2 {
            bottom: 10px;
            right: 15px;
            width: 60px;
            height: 30px;
            transform: rotate(20deg);
        }
        
        /* Big purple button for concept map */
        .big-purple-btn button {
            background-color: #8b5cf6 !important;
            color: white !important;
            border-radius: 999px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 14px 32px !important;
            font-size: 17px !important;
            width: 100% !important;
            visibility: visible !important;
            display: block !important;
        }
        
        /* Big buttons like start analysis button */
        .big-action-btn button {
            background-color: #8b5cf6 !important;
            color: white !important;
            border-radius: 10px !important;
            border: none !important;
            font-weight: 700 !important;
            padding: 20px 40px !important;
            font-size: 22px !important;
            width: 100% !important;
            height: auto !important;
            visibility: visible !important;
            display: block !important;
        }
        
    </style>
    """,
        unsafe_allow_html=True,
    )
    
    # Check if we just came from concept map and scroll to top
    if st.session_state.get("_from_concept_map", False):
        st.markdown("""
        <script>
            window.scrollTo(0, 0);
        </script>
        """, unsafe_allow_html=True)
        st.session_state["_from_concept_map"] = False

    # --------- GET TOPICS FROM ANALYSIS RESULT ----------
    result = st.session_state.get("analysis_result")
    
    # Map importance to color and subtitle
    importance_mapping = {
        "exam_critical": {
            "color": "dot-red",
            "subtitle": "Exam-critical — deeper understanding required",
        },
        "core": {
            "color": "dot-yellow",
            "subtitle": "Core concept — focus on intuition",
        },
        "extra": {
            "color": "dot-green",
            "subtitle": "Extra — helpful but not essential",
        },
    }
    
    # Show extraction errors if any
    if result and result.get("extraction_errors"):
        st.warning("⚠️ Some files had extraction issues: " + "; ".join(result["extraction_errors"][:3]))
        if len(result["extraction_errors"]) > 3:
            st.caption(f"... and {len(result['extraction_errors']) - 3} more")
    
    if result and result.get("topics"):
        # Use real analysis results
        raw_topics = result["topics"]
        topics = []
        for t in raw_topics:
            importance = t.get("importance", "extra")
            mapping = importance_mapping.get(importance, importance_mapping["extra"])
            topics.append({
                "name": t.get("name", "Unknown topic"),
                "importance_color": mapping["color"],
                "subtitle": mapping["subtitle"],
                "importance": importance,  # Keep for reference
            })
    else:
        # Fallback to static topics if no analysis result
        topics = [
            {
                "name": "Backpropagation & Gradient Descent",
                "importance_color": "dot-red",
                "subtitle": "Exam-critical — deeper understanding required",
            },
            {
                "name": "Activation Functions",
                "importance_color": "dot-yellow",
                "subtitle": "Core concept — focus on intuition",
            },
            {
                "name": "Dropout & BatchNorm",
                "importance_color": "dot-green",
                "subtitle": "Extra — helpful but not essential",
            },
        ]

    # --------- PAGE CONTENT ----------
    # Split page into two columns
    left_col, right_col = st.columns([1, 1], gap="large")
    
    with left_col:
        st.markdown(
            '<h1 class="dashboard-title">Your Key Topics</h1>',
            unsafe_allow_html=True,
        )
        
        # Topic cards (no Why buttons)
        for t in topics:
            st.markdown(
                f"""
                <div class="topic-card">
                    <div class="dot {t['importance_color']}"></div>
                    <div class="topic-main">
                        <div class="topic-title">{t['name']}</div>
                        <div class="topic-subtitle">{t['subtitle']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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
    
    
    with right_col:
        # Concept Map button with hand-drawn style and curved line
        st.markdown("""
        <div style="position: relative; margin-bottom: 25px;">
            <svg style="position: absolute; top: -10px; left: -15px; width: 120%; height: 120%; pointer-events: none; z-index: 0;">
                <path d="M 10 30 Q 40 10, 70 25 T 130 20" stroke="#8b5cf6" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0.6" style="filter: drop-shadow(1px 1px 1px rgba(0,0,0,0.1));"/>
            </svg>
            <div style="position: relative; z-index: 1;">
        """, unsafe_allow_html=True)
        
        if st.button("🗺️ Click to find out how topics connect to each other!", key="view_map_btn", use_container_width=True):
            st.session_state["page"] = "concept_map"
            st.rerun()
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        st.markdown("""
        <style>
        button[key="view_map_btn"] {
            background: white !important;
            border: 3px dashed #8b5cf6 !important;
            border-radius: 15px !important;
            padding: 20px 30px !important;
            font-family: 'Comic Sans MS', 'Marker Felt', 'Comic Neue', cursive !important;
            font-size: 18px !important;
            color: #6b21a8 !important;
            font-weight: 600 !important;
            text-align: center !important;
            transform: rotate(-1deg) !important;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1) !important;
            position: relative !important;
        }
        button[key="view_map_btn"]:hover {
            transform: rotate(0.5deg) scale(1.02) !important;
            box-shadow: 3px 5px 12px rgba(0,0,0,0.15) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.write("")  # spacer
        
        # Upload button with hand-drawn style and curved line
        st.markdown("""
        <div style="position: relative; margin-bottom: 25px;">
            <svg style="position: absolute; top: -8px; right: -10px; width: 110%; height: 110%; pointer-events: none; z-index: 0;">
                <path d="M 100 25 Q 70 15, 40 20 T 5 18" stroke="#8b5cf6" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0.6" style="filter: drop-shadow(1px 1px 1px rgba(0,0,0,0.1));"/>
            </svg>
            <div style="position: relative; z-index: 1;">
        """, unsafe_allow_html=True)
        
        if st.button("📄 Upload new slides here", key="reset_btn", use_container_width=True):
            # Save current session before resetting (only if it's a new session, not already saved)
            if "analysis_result" in st.session_state:
                # Collect all chat data
                chats = {}
                for key in list(st.session_state.keys()):
                    if key.startswith("topic_chat_") or key.startswith("edge_chat_") or key == "dashboard_chat_messages":
                        chats[key] = st.session_state[key]
                
                # Create session name from file names
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
                    # Save session
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
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        st.markdown("""
        <style>
        button[key="reset_btn"] {
            background: white !important;
            border: 3px dashed #8b5cf6 !important;
            border-radius: 15px !important;
            padding: 20px 30px !important;
            font-family: 'Comic Sans MS', 'Marker Felt', 'Comic Neue', cursive !important;
            font-size: 18px !important;
            color: #6b21a8 !important;
            font-weight: 600 !important;
            text-align: center !important;
            transform: rotate(1deg) !important;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1) !important;
            position: relative !important;
        }
        button[key="reset_btn"]:hover {
            transform: rotate(-0.5deg) scale(1.02) !important;
            box-shadow: 3px 5px 12px rgba(0,0,0,0.15) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.write("")  # spacer
        
        # ---- Chat component in right column ----
        show_dashboard_chat()
    
    # Chat input must be outside columns
    handle_dashboard_chat_input()