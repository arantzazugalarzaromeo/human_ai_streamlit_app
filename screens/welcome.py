# screens/welcome.py
import streamlit as st
import os

def show_welcome():
    # Check if we need to show undo option after reset
    if st.session_state.get("_reset_performed", False):
        st.warning("⚠️ Reset performed. You can undo this action if you didn't mean to upload new files.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Reset", key="confirm_reset_welcome"):
                st.session_state["_reset_performed"] = False
                if "_reset_backup" in st.session_state:
                    del st.session_state["_reset_backup"]
                st.rerun()
        with col2:
            if st.button("↩️ Undo Reset", key="undo_reset_welcome"):
                # Restore from backup
                if "_reset_backup" in st.session_state:
                    backup = st.session_state["_reset_backup"]
                    for key, value in backup.items():
                        st.session_state[key] = value
                    del st.session_state["_reset_backup"]
                st.session_state["_reset_performed"] = False
                # Go back to the page they were on (or dashboard if we have analysis_result)
                if "analysis_result" in st.session_state:
                    st.session_state["page"] = "dashboard"
                else:
                    st.session_state["page"] = "welcome"
                st.rerun()
    
    # --------- CSS ----------
    st.markdown(
        """
    <style>
        #MainMenu, header, footer {visibility: hidden;}

        .main .block-container {
            max-width: 1400px !important;
            padding-top: 3rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }
        
        /* Style session buttons like ChatGPT - tiny square rectangle, white with borders */
        button[key^="restore_session_"] {
            background: #ffffff !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 4px !important;
            padding: 8px 12px !important;
            margin-bottom: 6px !important;
            cursor: pointer !important;
            transition: all 0.15s !important;
            text-align: left !important;
            box-shadow: none !important;
            color: #1a0d2e !important;
            font-weight: 400 !important;
            font-size: 13px !important;
            width: 100% !important;
            height: auto !important;
            line-height: 1.4 !important;
            white-space: normal !important;
        }
        button[key^="restore_session_"]:hover {
            background: #f9fafb !important;
            border-color: #d1d5db !important;
        }

        .title-center {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1a0d2e;
            letter-spacing: -1px;
            font-size: 46px;
            font-weight: 700;
        }

        .subtitle-center {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #6b46c1;
            font-size: 20px;
        }

        .body-center {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #4b5563;
            font-size: 15px;
        }

        .upload-message {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #6b21a8;
            font-size: 17px;
            font-weight: 600;
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

        .start-btn button {
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

    # Initialize previous sessions storage
    if "previous_sessions" not in st.session_state:
        st.session_state["previous_sessions"] = []
    
    # --------- PAGE CONTENT ----------
    # Split into narrow sidebar and wide main content (ChatGPT-style layout)
    sidebar_col, main_col = st.columns([1, 6], gap="large")
    
    with sidebar_col:
        st.markdown("### 📚 Previous Sessions")
        previous_sessions = st.session_state.get("previous_sessions", [])
        if previous_sessions:
            for idx, session in enumerate(previous_sessions):
                session_name = session.get("name", f"Session {idx + 1}")
                file_count = len(session.get("saved_files", []))
                analysis_result = session.get("analysis_result", {})
                topic_count = len(analysis_result.get("topics", [])) if analysis_result else 0
                
                col_session, col_delete = st.columns([3, 1])
                with col_session:
                    # Create button with session name (ChatGPT style - clean text)
                    button_text = f"{session_name}"
                    if st.button(button_text, key=f"restore_session_{idx}", use_container_width=True):
                        # Restore session
                        st.session_state["analysis_result"] = session.get("analysis_result")
                        st.session_state["saved_files"] = session.get("saved_files", [])
                        st.session_state["uploaded_files"] = session.get("uploaded_files")
                        
                        # Restore all chats
                        for key, value in session.get("chats", {}).items():
                            st.session_state[key] = value
                        
                        st.session_state["page"] = "dashboard"
                        st.rerun()
                
                with col_delete:
                    if st.button("🗑️", key=f"delete_session_{idx}", help="Delete session"):
                        st.session_state["previous_sessions"].pop(idx)
                        st.rerun()
                
                st.write("")  # spacer between sessions
        else:
            st.info("No previous sessions. Upload files to create your first session!")
    
    with main_col:
        # Center everything in the main column
        left_spacer, center_content, right_spacer = st.columns([1, 3, 1])
        with center_content:
            st.markdown(
                "<h1 class='title-center'>Study Less. Understand More.</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p class='upload-message'>Upload your slides<br>"
                "and we'll highlight what actually matters for your exam.</p>",
                unsafe_allow_html=True,
            )
            
            st.write("")  # spacer
            
            uploaded_files = st.file_uploader(
                "Drag and drop files here",
                type=["pdf", "pptx", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
            )

            st.markdown(
                "<p class='body-center' style='margin-top:0.5rem;'>PDF, PPTX, Images — Drag & Drop or Click</p>",
                unsafe_allow_html=True,
            )

            if uploaded_files:
                # Validate files before saving
                from utils.file_validation import validate_files
                
                os.makedirs("uploads", exist_ok=True)
                temp_saved_files = []
                
                # Save files temporarily for validation
                for f in uploaded_files:
                    path = os.path.join("uploads", f.name)
                    with open(path, "wb") as buf:
                        buf.write(f.getbuffer())
                    temp_saved_files.append(path)
                
                # Validate files
                is_valid, valid_files, error_msg = validate_files(temp_saved_files)
                
                if not is_valid:
                    # Remove invalid files
                    for f in temp_saved_files:
                        if f not in valid_files and os.path.exists(f):
                            try:
                                os.remove(f)
                            except:
                                pass
                    st.error(f"❌ {error_msg}")
                    st.info("💡 Please upload files smaller than 50 MB each, with total size under 200 MB.")
                else:
                    st.session_state["uploaded_files"] = uploaded_files
                    st.session_state["saved_files"] = valid_files
                    
                    if error_msg:
                        st.warning(f"⚠️ {error_msg}")
                        st.success(f"✅ Successfully uploaded {len(valid_files)} file(s).")
                    else:
                        st.success(f"✅ Successfully uploaded {len(valid_files)} file(s).")
                    
                    st.write("")  # spacer
                    
                    # Center the button
                    st.markdown("<div class='start-btn'>", unsafe_allow_html=True)
                    if st.button("Start analysis", use_container_width=True):
                        # Run analysis and go directly to dashboard
                        st.session_state["analysis_start_time"] = None
                        from analysis.pipeline import analyze_files
                        saved_files = st.session_state.get("saved_files", [])
                        if saved_files:
                            try:
                                with st.spinner("🔄 Analyzing your slides..."):
                                    result = analyze_files(saved_files)
                                    st.session_state["analysis_result"] = result
                            except Exception as e:
                                st.error(f"❌ Analysis failed: {str(e)}")
                                st.rerun()
                        st.session_state["page"] = "dashboard"
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
