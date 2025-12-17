# components/topic_chat.py
import streamlit as st
from typing import Optional, List, Dict

from services.mistral_service import ask_mistral_about_topic
from services.rag_service import retrieve_relevant_snippets
from utils.safe_render import safe_markdown


# Evaluation display function removed - evaluator works invisibly
def _display_evaluation_removed(evaluation: Dict):
    """Display evaluation scores in a clean, transparent format."""
    if not evaluation:
        return
    
    # Introduction explaining what this evaluation is
    st.info(
        "💡 **Transparency Note:** This response was automatically evaluated by an AI quality checker "
        "to ensure accuracy, appropriate depth, and helpfulness. Scores are based on alignment with your "
        "uploaded materials and exam preparation needs."
    )
    
    # Define criteria labels with clear descriptions
    criteria_labels = {
        "correctness_alignment": {
            "label": "✅ Correctness & Alignment",
            "description": "How accurate and aligned with your uploaded materials"
        },
        "depth_matching": {
            "label": "🎯 Depth Matching",
            "description": "Whether the depth matches the topic importance (exam-critical vs. extra)"
        },
        "clarity_structure": {
            "label": "📝 Clarity & Structure",
            "description": "How clear, well-organized, and easy to follow"
        },
        "relevance_coverage": {
            "label": "📚 Relevance & Coverage",
            "description": "How relevant to exam preparation and coverage of key concepts"
        },
        "cognitive_load_tone": {
            "label": "💬 Cognitive Load & Tone",
            "description": "Friendliness, reassurance, and appropriate complexity"
        },
        "practice_question_quality": {
            "label": "❓ Practice Question Quality",
            "description": "Relevance, difficulty, and exam-style appropriateness"
        },
        "honesty_uncertainty": {
            "label": "🔍 Honesty About Uncertainty",
            "description": "Acknowledgment of limitations and avoiding overconfidence"
        },
    }
    
    # Score interpretation guide
    st.markdown("**Score Guide:** 🟢 Excellent (4-5) | 🟡 Good (3) | 🔴 Needs Improvement (1-2)")
    st.markdown("---")
    
    # Display each criterion with full transparency
    for key, info in criteria_labels.items():
        if key in evaluation:
            criterion = evaluation[key]
            score = criterion.get("score")
            explanation = criterion.get("explanation", "")
            
            col1, col2 = st.columns([2, 3])
            with col1:
                if score is not None:
                    # Color code based on score
                    if score >= 4:
                        color = "🟢"
                        confidence = "High"
                    elif score >= 3:
                        color = "🟡"
                        confidence = "Moderate"
                    else:
                        color = "🔴"
                        confidence = "Low"
                    
                    st.markdown(f"**{info['label']}**")
                    st.markdown(f"{color} **{score}/5** ({confidence} confidence)")
                    st.caption(f"*{info['description']}*")
                else:
                    st.markdown(f"**{info['label']}**")
                    st.markdown("N/A")
                    st.caption(f"*{info['description']}*")
            
            with col2:
                if explanation:
                    st.markdown(f"*{explanation}*")
                else:
                    st.markdown("*No detailed explanation available*")
            
            st.markdown("")  # Spacer
    
    # Calculate and show average score with confidence level
    scores = [criterion.get("score") for criterion in evaluation.values() 
              if isinstance(criterion, dict) and criterion.get("score") is not None]
    if scores:
        avg_score = sum(scores) / len(scores)
        
        # Determine overall confidence
        if avg_score >= 4:
            overall_confidence = "High"
            confidence_emoji = "🟢"
            confidence_msg = "This response meets high quality standards."
        elif avg_score >= 3:
            overall_confidence = "Moderate"
            confidence_emoji = "🟡"
            confidence_msg = "This response is generally good but may have some areas for improvement."
        else:
            overall_confidence = "Low"
            confidence_emoji = "🔴"
            confidence_msg = "This response may need revision or additional context."
        
        st.markdown("---")
        st.markdown(f"**Overall Quality Score**: {confidence_emoji} **{avg_score:.1f}/5** ({overall_confidence} confidence)")
        st.caption(f"*{confidence_msg}*")
        
        # Show how many criteria were evaluated
        st.caption(f"*Evaluated across {len(scores)} quality dimensions*")
    
    # Trust-building footer
    st.markdown("---")
    st.caption(
        "🔒 **Your Trust Matters:** This evaluation helps ensure the AI tutor provides accurate, "
        "helpful, and appropriately tailored responses. If you notice any issues, please let us know!"
    )


def _infer_importance_label(subtitle: Optional[str]) -> str:
    """
    Turn the subtitle text ('Exam-critical — ...', 'Core concept — ...', etc.)
    into a short label to feed the model.
    """
    if not subtitle:
        return "general topic"

    text = subtitle.lower()
    if "exam-critical" in text or "exam critical" in text:
        return "exam-critical topic that will almost certainly appear in the exam"
    if "core concept" in text:
        return "core concept that is important for the exam"
    if "extra" in text:
        return "extra / nice-to-have topic that is less likely to be examined"

    return "general topic"


def show_topic_chat(topic_name: str, importance_subtitle: Optional[str] = None) -> None:
    """
    Chat panel for a specific topic.

    - Keeps your existing chat UI (st.chat_message etc.)
    - Uses Mistral + LangChain (ask_mistral_about_topic) for answers.
    """

    chat_key = f"topic_chat_{topic_name}"
    auto_explained_key = f"{chat_key}_auto_explained"

    # --------- AUTO-START EXPLANATION WHEN TOPIC IS SELECTED ----------
    if chat_key not in st.session_state:
        # Auto-generate initial explanation at correct depth
        importance_label = _infer_importance_label(importance_subtitle)
        
        # Step 1: Understand the topic (get synonyms/related terms)
        # This is done inside retrieve_relevant_snippets now
        
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
        
        # Auto-start explanation - start with brief overview only
        try:
            # Initialize part tracking
            part_tracking_key = f"{chat_key}_part"
            st.session_state[part_tracking_key] = 0  # Start with part 0 (overview)
            
            auto_question = (
                f"Give me a brief overview of what I need to know about {topic_name} for exam preparation. "
                f"This is a {importance_label}. "
                "IMPORTANT: Start with just ONE small paragraph (3-4 sentences) giving a brief overview of the topic. "
                "Then add a tiny 2-sentence summary starting with 'In summary:' that tells me exactly what I need to know. "
                "Keep it SHORT - just an overview, not everything. "
                "After the summary, say: 'Would you like to continue learning about this topic, or do you want to understand this part better before moving on?' "
                "Make it easy to understand, reassuring, and written like a smart friend. "
                "Don't explain everything at once - just give a brief overview first."
            )
            
            with st.spinner("Preparing your personalized explanation..."):
                answer = ask_mistral_about_topic(
                    topic_name=topic_name,
                    importance_label=importance_label,
                    question=auto_question,
                    context_snippets=context_snippets if context_snippets else None,
                )
            
            st.session_state[chat_key] = [
                {"role": "assistant", "content": answer},
            ]
            st.session_state[auto_explained_key] = True
        except Exception as e:
            # Fallback if auto-explanation fails
            intro = (
                f"Let's focus on **{topic_name}**.\n\n"
                "I'm your AI study coach. I'll help you understand this at the right exam depth.\n\n"
                "Ask me to explain what you need to know about this topic!"
            )
            st.session_state[chat_key] = [
                {"role": "assistant", "content": intro},
            ]
            st.session_state[auto_explained_key] = False

    # --------- RENDER HISTORY ----------
    # Find the last assistant message index to show evaluation only there
    last_assistant_idx = None
    for idx in range(len(st.session_state[chat_key]) - 1, -1, -1):
        if st.session_state[chat_key][idx]["role"] == "assistant":
            last_assistant_idx = idx
            break
    
    for idx, msg in enumerate(st.session_state[chat_key]):
        with st.chat_message(msg["role"]):
            safe_markdown(msg["content"])
            
            # Evaluator works invisibly - students only see perfected responses

    # --------- CHECK FOR PENDING USER MESSAGES (from buttons) ----------
    # If last message is from user and no assistant reply yet, generate response
    pending_key = f"{chat_key}_pending_response"
    
    if (st.session_state[chat_key] and 
        st.session_state[chat_key][-1]["role"] == "user"):
        # Check if we already responded to this user message
        # (i.e., if the second-to-last message is an assistant message)
        needs_response = True
        if len(st.session_state[chat_key]) >= 2:
            # If second-to-last is assistant, we already responded
            if st.session_state[chat_key][-2]["role"] == "assistant":
                needs_response = False
        
        if needs_response and pending_key not in st.session_state:
            st.session_state[pending_key] = True
            
            # Get the last user message
            user_question = st.session_state[chat_key][-1]["content"]
            
            # Build importance label for the model
            importance_label = _infer_importance_label(importance_subtitle)
            
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
            
            try:
                with st.spinner("Thinking..."):
                    answer = ask_mistral_about_topic(
                        topic_name=topic_name,
                        importance_label=importance_label,
                        question=user_question,
                        context_snippets=context_snippets if context_snippets else None,
                    )
            except Exception as e:
                answer = (
                    "⚠️ **Error**\n\n"
                    f"Error: `{str(e)}`\n\n"
                    "Please check your API key and try again."
                )
                evaluation = None
            
            # Add assistant reply (already perfected by evaluator)
            st.session_state[chat_key].append({"role": "assistant", "content": answer})
            del st.session_state[pending_key]
            st.rerun()

    # --------- USER INPUT ----------
    placeholder = f"Ask something about {topic_name}..."
    user_input = st.chat_input(placeholder)

    if user_input:
        # Add user message
        st.session_state[chat_key].append({"role": "user", "content": user_input})

        # Build importance label for the model
        importance_label = _infer_importance_label(importance_subtitle)
        
        # Check if user is confirming understanding to move to next part
        part_tracking_key = f"{chat_key}_part"
        current_part = st.session_state.get(part_tracking_key, 0)
        
        # Detect if user wants to move to next part (keywords like "yes", "understood", "next", "continue", etc.)
        user_lower = user_input.lower().strip()
        move_to_next = any(word in user_lower for word in ["yes", "understood", "got it", "next", "continue", "move on", "ready", "ok", "okay", "sure"])
        re_explain = any(word in user_lower for word in ["no", "don't understand", "confused", "re-explain", "explain again", "repeat"])
        
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

        try:
            # Build question based on whether user wants to continue or needs re-explanation
            if move_to_next or any(word in user_lower for word in ["continue", "next", "more", "go on", "keep going"]):
                # User wants to continue learning
                st.session_state[part_tracking_key] = current_part + 1
                question = (
                    f"Great! Let's continue learning about {topic_name}. "
                    f"Explain the next important aspect in ONE compact paragraph (3-4 sentences). "
                    f"After the paragraph, add a tiny 2-sentence summary starting with 'In summary:'. "
                    f"Then ask: 'Would you like to continue learning about this topic, or do you want to understand this part better before moving on?' "
                    f"Keep it SHORT and COMPACT. If you've explained everything about this topic, say: 'I've told you everything you need to know about this topic. Let me know if you want to learn about a new topic or if you want some practice questions.'"
                )
            elif re_explain or any(word in user_lower for word in ["understand better", "explain again", "don't get it", "confused"]):
                # Re-explain current part
                question = (
                    f"No problem! Let me explain this part of {topic_name} in a different way. "
                    f"Explain it in ONE compact paragraph (3-4 sentences). "
                    f"After the paragraph, add a tiny 2-sentence summary starting with 'In summary:'. "
                    f"Then ask: 'Would you like to continue learning about this topic, or do you want to understand this part better before moving on?' "
                    f"Keep it SHORT and COMPACT."
                )
            else:
                # Regular question - check if last message was asking to continue
                if st.session_state[chat_key] and len(st.session_state[chat_key]) >= 2:
                    last_assistant = st.session_state[chat_key][-2]
                    if last_assistant.get("role") == "assistant" and ("continue learning" in last_assistant.get("content", "").lower() or "understand this part better" in last_assistant.get("content", "").lower()):
                        # User is responding to continue question - treat as continue
                        st.session_state[part_tracking_key] = current_part + 1
                        question = (
                            f"Great! Let's continue learning about {topic_name}. "
                            f"Explain the next important aspect in ONE compact paragraph (3-4 sentences). "
                            f"After the paragraph, add a tiny 2-sentence summary starting with 'In summary:'. "
                            f"Then ask: 'Would you like to continue learning about this topic, or do you want to understand this part better before moving on?' "
                            f"Keep it SHORT and COMPACT. If you've explained everything about this topic, say: 'I've told you everything you need to know about this topic. Let me know if you want to learn about a new topic or if you want some practice questions.'"
                        )
                    else:
                        # Regular question
                        question = user_input
                else:
                    question = user_input
            
            # Call Mistral through our helper (with RAG context)
            with st.spinner("Thinking..."):
                answer = ask_mistral_about_topic(
                    topic_name=topic_name,
                    importance_label=importance_label,
                    question=question,
                    context_snippets=context_snippets if context_snippets else None,
                )
        except RuntimeError as e:
            # API key missing or configuration error
            answer = (
                "⚠️ **Configuration Error**\n\n"
                f"{str(e)}\n\n"
                "Please set your MISTRAL_API_KEY in a `.env` file or as an environment variable.\n\n"
                "**To fix this:**\n"
                "1. Create a `.env` file in the project root\n"
                "2. Add: `MISTRAL_API_KEY=your_api_key_here`\n"
                "3. Restart Streamlit"
            )
        except Exception as e:
            # Other errors (network, API, etc.)
            answer = (
                "⚠️ **Error connecting to Mistral AI**\n\n"
                f"Error: `{str(e)}`\n\n"
                "This could be due to:\n"
                "- Invalid API key\n"
                "- Network connectivity issues\n"
                "- API rate limits\n\n"
                "Please check your API key and try again."
            )

        # Add assistant reply (already perfected by evaluator)
        st.session_state[chat_key].append(
            {"role": "assistant", "content": answer}
        )

        # Rerun so the new messages show immediately
        st.rerun()
