# components/chat.py
import streamlit as st
from typing import Dict

try:
    from services.dashboard_chat_service import ask_about_rankings
    HAS_MISTRAL = True
except Exception:
    HAS_MISTRAL = False

from utils.safe_render import safe_markdown


# Evaluation display functions removed - evaluator works invisibly


def show_dashboard_chat() -> None:
    """
    Chat panel for dashboard that explains topic rankings using Mistral.
    Shows chat history (can be inside columns).
    """
    chat_key = "dashboard_chat_messages"

    # Get topics from analysis result
    result = st.session_state.get("analysis_result")
    topics = result.get("topics", []) if result else []

    # --------- INITIAL HISTORY ----------
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {
                "role": "assistant",
                "content": (
                    "Hi! I'm your study coach. Here's what you can ask me:\n\n"
                    "- Understand why each topic was ranked there\n\n"
                    "- Learn about a specific topic from the list\n\n"
                    "- Understand how topics connect to each other\n\n"
                    "- Get practice questions for any topic"
                ),
            }
        ]

    # --------- HEADER TEXT ----------
    st.markdown("### Ask the AI tutor")
    

    # --------- RENDER CHAT HISTORY ----------
    for idx, msg in enumerate(st.session_state[chat_key]):
        with st.chat_message(msg["role"]):
            safe_markdown(msg["content"])
            # Evaluator works invisibly - students only see perfected responses


def handle_dashboard_chat_input() -> None:
    """
    Handle chat input for dashboard (must be called outside columns).
    """
    chat_key = "dashboard_chat_messages"
    
    # Get topics from analysis result
    result = st.session_state.get("analysis_result")
    topics = result.get("topics", []) if result else []
    
    # --------- USER INPUT ----------
    user_input = st.chat_input("Type your question about these topics...")
    if user_input:
        # Check if this message was already processed (prevent duplicates)
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []
        
        # Only process if last message is not the same user input (prevent duplicates)
        last_message = st.session_state[chat_key][-1] if st.session_state[chat_key] else None
        if last_message and last_message.get("role") == "user" and last_message.get("content") == user_input:
            # Already processing this message, skip
            return
        
        # Add user message to session state
        st.session_state[chat_key].append({"role": "user", "content": user_input})
        
        # Track teaching progress (for progressive teaching)
        teaching_topic_key = f"{chat_key}_teaching_topic"
        teaching_part_key = f"{chat_key}_teaching_part"
        current_teaching_topic = st.session_state.get(teaching_topic_key)
        current_part = st.session_state.get(teaching_part_key, 0)
        
        # Check if this is a teaching continuation
        question_lower = user_input.lower()
        is_teaching_question = any(word in question_lower for word in ["teach", "explain", "learn about", "what is", "tell me about"])
        is_continue = any(word in question_lower for word in ["continue", "next", "more", "go on", "yes", "understood", "ok", "okay"])
        
        # Check if last assistant message was asking to continue
        if len(st.session_state[chat_key]) >= 2:
            last_assistant = st.session_state[chat_key][-2]
            if last_assistant.get("role") == "assistant" and ("continue learning" in last_assistant.get("content", "").lower() or "understand this part better" in last_assistant.get("content", "").lower()):
                # User is responding to continue question
                if current_teaching_topic:
                    is_continue = True
        
        if is_teaching_question:
            # Extract topic name for tracking
            from services.dashboard_chat_service import _extract_topic_names
            topic_info = _extract_topic_names(user_input, topics)
            if topic_info and topic_info[0]:
                st.session_state[teaching_topic_key] = topic_info[0]
                st.session_state[teaching_part_key] = 0
                current_part = 0
        elif is_continue and current_teaching_topic:
            # Continue teaching
            st.session_state[teaching_part_key] = current_part + 1
            current_part = current_part + 1
        
        # Get answer from Mistral if available
        try:
            if HAS_MISTRAL and topics:
                with st.spinner("Thinking..."):
                    result = st.session_state.get("analysis_result")
                    text_dict = result.get("text_dict") if result else None
                    structured_slides = result.get("structured_slides") if result else None
                    # Pass chat history so teaching chain knows what was already taught
                    chat_history = st.session_state[chat_key][:-1] if len(st.session_state[chat_key]) > 1 else []
                    answer = ask_about_rankings(topics, user_input, text_dict, structured_slides, current_part if current_teaching_topic else None, current_teaching_topic, chat_history)
            else:
                answer = (
                    "⚠️ **Mistral API not configured**\n\n"
                    "To get intelligent explanations, please set your MISTRAL_API_KEY in a `.env` file.\n\n"
                    f"For now, I'm acknowledging your question: {user_input}"
                )
        except Exception as e:
            answer = (
                "⚠️ **Error connecting to Mistral AI**\n\n"
                f"Error: `{str(e)}`\n\n"
                "Please check your API key and try again."
            )
        
        # Add assistant reply (already perfected by evaluator)
        st.session_state[chat_key].append({"role": "assistant", "content": answer})
        
        # Rerun to display the new messages
        st.rerun()
