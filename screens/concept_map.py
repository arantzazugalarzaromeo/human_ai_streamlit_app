# screens/concept_map.py
import streamlit as st
import graphviz


def _wrap_text(text: str, max_line_length: int = 20) -> str:
    """
    Wrap text into multiple lines to fit inside node.
    Splits at spaces to avoid breaking words.
    Returns text with \\n for Graphviz line breaks.
    """
    if len(text) <= max_line_length:
        return text
    
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        # If adding this word would exceed max length, start a new line
        if current_line and len(current_line) + len(word) + 1 > max_line_length:
            lines.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Join with newline for Graphviz
    return "\n".join(lines)


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


def show_concept_map():
    # --------- CSS ----------
    st.markdown(
        """
    <style>
        #MainMenu, header, footer {visibility: hidden;}

        .main .block-container {
            max-width: 100% !important;
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            margin: 0 auto !important;
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
        
        /* Close button - big and clear */
        button[key="close_fullscreen"] {
            background-color: #ef4444 !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 700 !important;
            padding: 18px 40px !important;
            font-size: 22px !important;
            width: 100% !important;
            visibility: visible !important;
            display: block !important;
        }
    </style>
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
    
    # --------- GET TOPICS FROM ANALYSIS RESULT ----------
    result = st.session_state.get("analysis_result")
    
    if result and result.get("topic_graph"):
        # Use real analysis results
        graph = result["topic_graph"]
        topics = graph.get("nodes", [])
        edges_list = graph.get("edges", [])
    else:
        # Fallback to static topics
        topics = [
            {
                "id": "backprop",
                "label": "Backpropagation & Gradient Descent",
                "importance": "exam_critical",
            },
            {
                "id": "activations",
                "label": "Activation Functions",
                "importance": "core",
            },
            {
                "id": "regularisation",
                "label": "Dropout & BatchNorm",
                "importance": "extra",
            },
        ]
        edges_list = [
            ("backprop", "activations"),
            ("backprop", "regularisation"),
            ("activations", "regularisation"),
        ]

    # Map importance -> subtitle text
    importance_subtitles = {
        "exam_critical": "Exam-critical — deeper understanding required",
        "core": "Core concept — focus on intuition",
        "extra": "Extra — helpful but not essential",
    }

    # Map importance -> colors (matching dashboard dots)
    importance_colors = {
        "exam_critical": "#f97373",  # red
        "core": "#facc15",  # yellow
        "extra": "#22c55e",  # green
    }

    # Map importance -> node sizes (all same size, normal size)
    # All nodes use the same size to ensure text fits properly
    uniform_node_size = "2.0"  # Large enough to fit text with wrapping

    # --------- BUILD GRAPHVIZ CONCEPT MAP ----------
    # Separate connected and unconnected nodes
    connected_node_ids = set()
    for edge in edges_list:
        if len(edge) == 2:
            connected_node_ids.add(edge[0])
            connected_node_ids.add(edge[1])
    
    unconnected_nodes = [t for t in topics if t.get("id") not in connected_node_ids]
    connected_nodes = [t for t in topics if t.get("id") in connected_node_ids]
    
    # Create graph with LR (left to right) layout for horizontal display
    dot = graphviz.Digraph()
    dot.attr(rankdir="LR")  # Left to right (horizontal)
    
    # Add unconnected nodes first (they'll appear on top)
    if unconnected_nodes:
        # Use invisible edges to keep unconnected nodes on same rank (horizontal line)
        unconnected_ids = [t.get("id") for t in unconnected_nodes]
        for i in range(len(unconnected_ids) - 1):
            dot.edge(unconnected_ids[i], unconnected_ids[i+1], style="invis")
        
        for t in unconnected_nodes:
            topic_id = t.get("id", "")
            topic_label = t.get("label", t.get("name", "Unknown"))
            importance = t.get("importance", "extra")
            color = importance_colors.get(importance, "#8b5cf6")
            
            # Wrap long labels to fit inside node (split at spaces, max ~20 chars per line)
            display_label = _wrap_text(topic_label, max_line_length=20)
            
            dot.node(
                topic_id,
                display_label,
                shape="ellipse",  # Ellipse fits text better than circle
                style="filled",
                fillcolor=color,
                color=color,
                fontname="Segoe UI",
                fontsize="10",
                fontcolor="#ffffff",
                width=uniform_node_size,
                height=uniform_node_size,
                fixedsize="true",  # Use exact size, don't scale
            )
    
    # Add connected nodes (they'll appear below)
    for t in connected_nodes:
        topic_id = t.get("id", "")
        topic_label = t.get("label", t.get("name", "Unknown"))
        importance = t.get("importance", "extra")
        color = importance_colors.get(importance, "#8b5cf6")
        
        # Wrap long labels to fit inside node (split at spaces, max ~20 chars per line)
        display_label = _wrap_text(topic_label, max_line_length=20)
        
        dot.node(
            topic_id,
            display_label,
            shape="ellipse",  # Ellipse fits text better than circle
            style="filled",
            fillcolor=color,
            color=color,
            fontname="Segoe UI",
            fontsize="10",
            fontcolor="#ffffff",
            width=uniform_node_size,
            height=uniform_node_size,
            fixedsize="true",  # Use exact size, don't scale
        )

    # Add actual edges (connections between topics) - directed (parent -> child)
    for edge in edges_list:
        if len(edge) == 2:
            # Directed edges: parent -> child (hierarchical tree structure)
            dot.edge(edge[0], edge[1], color="#8b5cf6", penwidth="2", dir="forward", arrowsize="0.8")

    # Always open in fullscreen mode
    # --------- PAGE CONTENT ----------
    # Fullscreen mode - larger display (always active)
    st.markdown("""
    <style>
        .stGraphviz {
            max-height: 90vh !important;
        }
        svg {
            max-height: 90vh !important;
            width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Concept map centered - fullscreen display
    left, centre, right = st.columns([1, 3, 1])
    with centre:
        st.graphviz_chart(dot, use_container_width=True)

    st.write("")  # spacer
    
    # Close button - goes back to ranking
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("❌ **CLOSE**", use_container_width=True, key="close_fullscreen"):
            st.session_state["page"] = "dashboard"
            st.session_state["_from_concept_map"] = True  # Flag to scroll to top
            st.rerun()
