# components/edge_chat.py
import streamlit as st
from typing import List, Dict

try:
    from services.edge_tutor_service import explain_topic_connection
    from services.rag_service import retrieve_co_occurrence_snippets
    HAS_EDGE_SERVICE = True
except Exception:
    HAS_EDGE_SERVICE = False

from utils.safe_render import safe_markdown


def _display_edge_evaluation(evaluation: Dict):
    """Display edge evaluation scores in a clean, transparent format."""
    if not evaluation:
        return
    
    st.info(
        "💡 **Transparency Note:** This connection explanation was automatically evaluated by an AI quality checker "
        "to ensure accuracy and helpfulness."
    )
    
    # Define criteria labels for edge evaluation
    criteria_labels = {
        "link_makes_sense": {
            "label": "🔗 Link Makes Sense",
            "description": "Does it describe a real, meaningful relationship?"
        },
        "respecting_edge_logic": {
            "label": "📊 Respects Edge Logic",
            "description": "Does it match the type of connection (hierarchical, same slide, etc.)?"
        },
        "grounding_correctness": {
            "label": "✅ Grounding & Correctness",
            "description": "Is it consistent with how topics are used in your materials?"
        },
    }
    
    st.markdown("**Score Guide:** 🟢 Excellent (4-5) | 🟡 Good (3) | 🔴 Needs Improvement (1-2)")
    st.markdown("---")
    
    # Display each criterion
    for key, info in criteria_labels.items():
        if key in evaluation:
            criterion = evaluation[key]
            score = criterion.get("score")
            explanation = criterion.get("explanation", "")
            
            col1, col2 = st.columns([2, 3])
            with col1:
                if score is not None:
                    if score >= 4:
                        color = "🟢"
                    elif score >= 3:
                        color = "🟡"
                    else:
                        color = "🔴"
                    
                    st.markdown(f"**{info['label']}**")
                    st.markdown(f"{color} **{score}/5**")
                    st.caption(f"*{info['description']}*")
            
            with col2:
                if explanation:
                    st.markdown(f"*{explanation}*")
            
            st.markdown("")
    
    # Show overall confidence
    if "overall_confidence" in evaluation:
        confidence = evaluation["overall_confidence"]
        st.markdown("---")
        st.markdown(f"**Overall Confidence: {confidence}%**")


def show_edge_chat(topic_a_label: str, topic_b_label: str, topic_a_id: str, topic_b_id: str):
    """Chat for explaining topic connections."""
    chat_key = f"edge_chat_{topic_a_id}_{topic_b_id}"
    
    # Initial message
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {
                "role": "assistant",
                "content": (
                    f"Let's explore how **{topic_a_label}** and **{topic_b_label}** connect.\n\n"
                    "Ask me things like:\n"
                    "- *How do these topics relate?*\n"
                    "- *Why is this connection important for the exam?*\n"
                    "- *What should I understand about how they work together?*"
                ),
            }
        ]
    
    # Render history
    for idx, msg in enumerate(st.session_state[chat_key]):
        with st.chat_message(msg["role"]):
            safe_markdown(msg["content"])
            # Evaluator works invisibly - students only see perfected responses
    
    # User input
    user_input = st.chat_input(f"Ask about how {topic_a_label} and {topic_b_label} connect...")
    
    if user_input:
        st.session_state[chat_key].append({"role": "user", "content": user_input})
        
        # Get context snippets
        context_snippets = []
        result = st.session_state.get("analysis_result")
        if result and result.get("text_dict"):
            context_snippets = retrieve_co_occurrence_snippets(
                topic_a_label,
                topic_b_label,
                result["text_dict"],
                max_snippets=3
            )
        
        try:
            if HAS_EDGE_SERVICE:
                with st.spinner("Thinking..."):
                    # Get edge signals from analysis result if available
                    edge_signals = "Topics appear together in slides (co-occurrence detected)"
                    result = st.session_state.get("analysis_result")
                    if result and result.get("topic_graph"):
                        edges = result["topic_graph"].get("edges", [])
                        # Check if this edge exists
                        for edge in edges:
                            if len(edge) == 2 and (edge[0] == topic_a_id and edge[1] == topic_b_id) or (edge[0] == topic_b_id and edge[1] == topic_a_id):
                                edge_signals = "Topics co-occur on same slide or have hierarchical relationship"
                                break
                    
                    answer = explain_topic_connection(
                        topic_a_label,
                        topic_b_label,
                        user_input,
                        context_snippets,
                        edge_signals=edge_signals
                    )
            else:
                answer = (
                    "⚠️ **Mistral API not configured**\n\n"
                    "Please set your MISTRAL_API_KEY to get intelligent explanations."
                )
        except Exception as e:
            answer = (
                "⚠️ **Error**\n\n"
                f"Error: `{str(e)}`\n\n"
                "Please check your API key and try again."
            )
        
        # Add assistant reply (already perfected by evaluator)
        st.session_state[chat_key].append({"role": "assistant", "content": answer})
        st.rerun()



