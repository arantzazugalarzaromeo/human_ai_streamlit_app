# screens/analyzing.py
import time
import streamlit as st

from analysis.pipeline import analyze_files  # step-1 pipeline


# --- run the backend analysis exactly once -----------------
def _ensure_analysis():
    if "analysis_result" in st.session_state:
        return

    saved_files = st.session_state.get("saved_files", [])
    if not saved_files:
        st.error("❌ No files uploaded. Please go back and upload files.")
        if st.button("← Back to upload"):
            st.session_state["page"] = "welcome"
            st.rerun()
        return

    try:
        result = analyze_files(saved_files)
        st.session_state["analysis_result"] = result
        
        # Check if we got any text at all
        if not result.get("text_dict") or not any(result.get("text_dict", {}).values()):
            st.warning("⚠️ No text could be extracted from the uploaded files. "
                      "The files may be empty, corrupted, or contain only images.")
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        st.info("💡 Please try uploading different files or check that your files are not corrupted.")
        if st.button("← Back to upload"):
            st.session_state["page"] = "welcome"
            st.rerun()
        return


def show_analyzing():
    # ---------- TIMER SETUP (start before analysis) ----------
    if (
        "analysis_start_time" not in st.session_state
        or st.session_state["analysis_start_time"] is None
    ):
        st.session_state["analysis_start_time"] = time.time()

    # ---------- RUN ANALYSIS (once) ----------
    _ensure_analysis()
    result = st.session_state.get("analysis_result")

    # Calculate actual elapsed time
    elapsed = time.time() - st.session_state["analysis_start_time"]
    elapsed_seconds = int(elapsed)

    # ---------- CSS (this is your original styling) ----------
    st.markdown(
        """
    <style>
        #MainMenu, header, footer {visibility: hidden;}

        /* same container width / centering as before */
        .main .block-container {
            max-width: 700px !important;
            padding-top: 4rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }

        .analyzing-title {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1a0d2e;
            font-size: 40px;
            font-weight: 700;
            margin-bottom: 2.5rem;
            letter-spacing: -0.5px;
        }

        .task-item {
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: center;
            gap: 14px;
            padding: 8px 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #4b5563;
            font-size: 17px;
        }

        .task-emoji {
            font-size: 24px;
        }

        .time-remaining {
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #6b7280;
            font-size: 17px;
            font-style: italic;
            margin-top: 3.5rem;
            line-height: 1.4;
        }

        /* loading spinner */
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .spinner {
            border: 4px solid #f3f4f6;
            border-top: 4px solid #8b5cf6;
            border-radius: 50%;
            width: 64px;
            height: 64px;
            animation: spin 1s linear infinite;
            margin: 0 auto 2.5rem;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ---------- PAGE CONTENT (same structure as before) ----------
    # spinner
    st.markdown('<div class="spinner"></div>', unsafe_allow_html=True)

    # main title
    st.markdown(
        '<h1 class="analyzing-title">Analyzing your material...</h1>',
        unsafe_allow_html=True,
    )

    # task list
    tasks = [
        ("📚", "Extracting key topics"),
        ("🎯", "Ranking topics by importance"),
        ("🔗", "Linking ideas and building concept map"),
    ]

    for emoji, text in tasks:
        st.markdown(
            f'<div class="task-item"><span class="task-emoji">{emoji}</span>'
            f"<span>{text}</span></div>",
            unsafe_allow_html=True,
        )

    # timer text - show actual elapsed time
    st.markdown(
        f'<p class="time-remaining">Time elapsed: {elapsed_seconds}s</p>',
        unsafe_allow_html=True,
    )

    # ---------- AUTO-REDIRECT ----------
    # Redirect immediately when analysis is complete
    if result is not None:
        # finished → reset timer and go to dashboard
        st.session_state["analysis_start_time"] = None
        st.session_state["page"] = "dashboard"
        st.rerun()
    else:
        # keep updating while analysis is running
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__":
    show_analyzing()
