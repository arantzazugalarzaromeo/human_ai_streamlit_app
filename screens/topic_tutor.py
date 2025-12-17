# screens/topic_tutor.py
import streamlit as st
import os
from components.topic_chat import show_topic_chat


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


def show_topic_tutor():
    # If no topic was selected, send user back to concept map
    topic = st.session_state.get("selected_topic")
    if topic is None:
        st.warning("No topic selected yet. Please choose a topic from the concept map.")
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

    topic_name = topic.get("name", "Selected topic")
    subtitle = topic.get("subtitle", "")

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

        .topic-title-main {
            text-align: left;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1a0d2e;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 0.25rem;
            letter-spacing: -0.5px;
        }

        .topic-subtitle-main {
            text-align: left;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #6b7280;
            font-size: 15px;
            margin-bottom: 1.5rem;
        }

        .topic-tag {
            display: inline-block;
            margin-top: 0.5rem;
            padding: 4px 10px;
            border-radius: 999px;
            background-color: #eef2ff;
            color: #4f46e5;
            font-size: 13px;
            font-weight: 500;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .section-caption {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 14px;
            color: #4b5563;
            margin-bottom: 1rem;
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

        .action-btn button {
            background-color: #8b5cf6 !important;
            color: white !important;
            border-radius: 999px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            font-size: 16px !important;
            visibility: visible !important;
            display: block !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # --------- PAGE CONTENT ----------
    # Everything in center column for consistent layout
    left, centre, right = st.columns([1, 2, 1])
    with centre:
        st.markdown(
            f"<h1 class='topic-title-main'>{topic_name}</h1>",
            unsafe_allow_html=True,
        )
        if subtitle:
            st.markdown(
                f"<p class='topic-subtitle-main'>{subtitle}</p>",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<span class='topic-tag'>AI tutor view for this topic</span>",
                unsafe_allow_html=True,
            )

            st.write("")  # spacer
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📝 Practice Questions", key="practice_btn"):
                    try:
                        from services.practice_questions_service import generate_practice_questions
                        from components.topic_chat import _infer_importance_label
                        
                        importance_label = _infer_importance_label(subtitle)
                        with st.spinner("Generating practice questions..."):
                            questions = generate_practice_questions(topic_name, importance_label)
                            
                            # Add to chat (questions already perfected by evaluator)
                            chat_key = f"topic_chat_{topic_name}"
                            if chat_key not in st.session_state:
                                st.session_state[chat_key] = []
                            st.session_state[chat_key].append({
                                "role": "assistant",
                                "content": f"**Practice Questions for {topic_name}:**\n\n{questions}"
                            })
                            st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate questions: {e}")
            
            with col2:
                # Determine button text based on importance
                importance_text = subtitle.split('—')[0].strip() if subtitle else "this importance"
                if "exam-critical" in importance_text.lower() or "exam critical" in importance_text.lower():
                    btn_text = "❓ Why Exam-Critical?"
                elif "core" in importance_text.lower():
                    btn_text = "❓ Why Core?"
                else:
                    btn_text = "❓ Why Extra?"
                
                if st.button(btn_text, key="why_btn"):
                    try:
                        from services.mistral_service import ask_mistral_about_topic
                        from services.rag_service import retrieve_relevant_snippets
                        from components.topic_chat import _infer_importance_label
                        
                        # Add question to chat
                        chat_key = f"topic_chat_{topic_name}"
                        if chat_key not in st.session_state:
                            st.session_state[chat_key] = []
                        
                        user_question = f"Why is '{topic_name}' marked as {importance_text}? Explain the reasoning in a friendly, easy-to-understand way."
                        st.session_state[chat_key].append({
                            "role": "user",
                            "content": user_question
                        })
                        
                        # Generate response immediately
                        importance_label = _infer_importance_label(subtitle)
                        
                        # Step 2: Retrieve relevant context using enhanced RAG (3 signals)
                        context_snippets = []
                        result = st.session_state.get("analysis_result")
                        if result and result.get("text_dict"):
                            # Get structured slides if available
                            structured_slides = result.get("structured_slides")
                            context_snippets = retrieve_relevant_snippets(
                                topic_name,
                                result["text_dict"],
                                structured_slides=structured_slides,
                                max_snippets=5  # Get top 5 snippets using 3 signals
                            )
                        
                        with st.spinner("Thinking..."):
                            answer = ask_mistral_about_topic(
                                topic_name=topic_name,
                                importance_label=importance_label,
                                question=user_question,
                                context_snippets=context_snippets if context_snippets else None,
                            )
                        
                        # Add assistant reply (already perfected by evaluator)
                        st.session_state[chat_key].append({
                            "role": "assistant",
                            "content": answer
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate answer: {e}")
                        # Still add the user question even if generation fails
                        chat_key = f"topic_chat_{topic_name}"
                        if chat_key not in st.session_state:
                            st.session_state[chat_key] = []
                        st.session_state[chat_key].append({
                            "role": "user",
                            "content": f"Why is '{topic_name}' marked as {importance_text}? Explain the reasoning in a friendly, easy-to-understand way."
                        })
                        st.rerun()

            st.write("")  # spacer

            st.markdown(
                "<p class='section-caption'>Chat with the AI tutor about this topic. "
                "Answers are grounded in your uploaded materials using RAG.</p>",
                unsafe_allow_html=True,
            )
            
            # Signifier: What can user do here?
            st.info("💡 **What you can do:** The tutor automatically explains what you need to know at the right depth. Use the buttons above for quick actions, or ask questions in the chat below.")

        # Topic-specific chat (now powered by Mistral)
        show_topic_chat(topic_name, subtitle)

        st.write("")  # small spacer at the bottom

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
