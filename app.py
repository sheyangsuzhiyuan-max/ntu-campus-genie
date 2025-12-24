import streamlit as st

from rag_pipeline import build_knowledge_base
from chat import run_chat, generate_housing_plan
from utils import get_feedback_stats, init_session_state
from config import EXAMPLE_QUESTIONS, DEFAULT_API_KEY

# --- 1. Page Configuration ---
st.set_page_config(page_title="NTU Genie", page_icon="🏫", layout="wide")

# Initialize session state
init_session_state()

# Compact header with custom styling
st.markdown(
    """
    <div style='padding: 0.5rem 0; margin-bottom: 0.5rem;'>
        <h2 style='margin: 0; padding: 0; font-size: 1.8rem;'>🏫 NTU Campus Genie</h2>
        <p style='margin: 0; padding: 0; font-size: 0.9rem; color: #666;'>AI-Powered Campus Assistant for Graduate Students</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- 2. Sidebar: Reorganized ---
with st.sidebar:
    # === Section 2: Setup (Always visible but compact) ===
    with st.expander("🔧 Setup", expanded=True):
        # API Key Input
        deepseek_api_key = st.text_input(
            "DeepSeek API Key",
            value=DEFAULT_API_KEY or "",
            type="password",
            help="Enter your DeepSeek API Key"
        )

        if not deepseek_api_key:
            st.markdown("[🔗 Get API Key](https://platform.deepseek.com/api-keys)")

    st.divider()

    # === Section 1: Compact Status Bar ===
    st.markdown("### ⚙️ Status")

    # API Status
    if DEFAULT_API_KEY or deepseek_api_key:
        api_status = "✅ API Ready"
    else:
        api_status = "⚠️ API Not Set"

    # KB Status
    if "doc_stats" in st.session_state and st.session_state["doc_stats"]:
        kb_status = "✅ KB Ready"
    else:
        kb_status = "⚠️ KB Not Loaded"

    # Compact status line
    st.caption(f"{api_status} | {kb_status}")

    st.divider()

    # === Section 3: Knowledge Base (Collapsed when ready) ===
    kb_expanded = "doc_stats" not in st.session_state or not st.session_state["doc_stats"]

    with st.expander("📚 Knowledge Base", expanded=kb_expanded):
        # Quick Start Button (primary action)
        if "doc_stats" not in st.session_state or not st.session_state["doc_stats"]:
            if st.button("🚀 Load Default KB", type="primary", use_container_width=True):
                if not deepseek_api_key:
                    st.error("❌ Enter API Key first!")
                else:
                    with st.spinner("Loading..."):
                        build_knowledge_base(use_default_files=True)
                    st.rerun()

            st.caption("💡 Includes: Housing, Visa, Campus Life, Academic guides")
        else:
            # KB loaded - show reset option
            st.success("✅ Knowledge Base Loaded")
            if st.button("🔄 Reset KB", use_container_width=True):
                if "vectorstore" in st.session_state:
                    del st.session_state["vectorstore"]
                if "doc_stats" in st.session_state:
                    del st.session_state["doc_stats"]
                st.rerun()

        st.divider()

        # Upload Custom Documents
        st.caption("**Or upload custom documents:**")

        uploaded_files = st.file_uploader(
            "📄 Files (PDF/TXT)",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        url_input = st.text_area(
            "🌐 URLs (one per line)",
            height=60,
            placeholder="https://example.com",
            label_visibility="collapsed"
        )
        urls = [line.strip() for line in url_input.split('\n') if line.strip()]

        # Build button
        if uploaded_files or urls:
            if st.button("🔄 Build Custom KB", use_container_width=True):
                if not deepseek_api_key:
                    st.error("❌ Enter API Key first!")
                else:
                    build_knowledge_base(uploaded_files=uploaded_files, urls=urls)

        # Show data sources
        if "doc_stats" in st.session_state and st.session_state["doc_stats"]:
            st.divider()
            with st.expander("📊 Data Sources", expanded=False):
                for stat in st.session_state["doc_stats"]:
                    st.caption(f"• {stat['type']} **{stat['name']}** ({stat['chars']:,} chars)")

    # === Section 4: Diagnostics (default collapsed) ===
    with st.expander("🔧 Diagnostics", expanded=False):
        st.caption("**Feedback Statistics:**")
        stats = get_feedback_stats()

        if stats["total"] == 0:
            st.caption("No feedback yet")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", stats["total"])
            with col2:
                st.metric("👍", stats["ups"])
            with col3:
                st.metric("👎", stats["downs"])

            if stats["recent"]:
                st.caption("**Recent 5:**")
                for r in stats["recent"]:
                    q = (r.get("question") or "")[:40]
                    st.caption(f"• {q}... | `{r.get('label')}`")

            # Download button
            import os
            from config import FEEDBACK_LOG_FILE
            if os.path.exists(FEEDBACK_LOG_FILE):
                with open(FEEDBACK_LOG_FILE, "r", encoding="utf-8") as f:
                    csv_data = f.read()
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name="feedback.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="sidebar_download_feedback"
                )

# --- 3. Main Content Area ---

# Status-driven Quick Start (only when KB not loaded)
if "vectorstore" not in st.session_state:
    # Lightweight prompt - no big callout
    st.caption("💡 Load the default knowledge base to start chatting with NTU Campus Genie")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Load Default Knowledge Base", type="primary", use_container_width=True, key="main_load_kb"):
            if not deepseek_api_key:
                st.error("❌ Please enter your DeepSeek API Key in the sidebar first")
            else:
                with st.spinner("Loading default knowledge base..."):
                    build_knowledge_base(use_default_files=True)
                st.rerun()

    st.divider()
    st.caption("Or configure custom knowledge base in the sidebar →")
    st.stop()

# === Tabs: Separate functional areas ===
tab1, tab2 = st.tabs(["💬 Chat", "🏠 Housing Wizard"])

# --- Tab 1: Chat (Main Stage) ---
with tab1:
    # Quick Start Questions - Show first 3 inline, rest in expander
    st.caption("**Quick Start:**")

    # Show first 3 questions as inline chips
    cols = st.columns(3)
    for i in range(min(3, len(EXAMPLE_QUESTIONS))):
        with cols[i]:
            question = EXAMPLE_QUESTIONS[i]
            short_q = question[:35] + "..." if len(question) > 35 else question
            if st.button(
                short_q,
                key=f"chip_inline_{i}",
                use_container_width=True,
                help=question
            ):
                st.session_state["prefill"] = question
                st.rerun()

    # Rest in expander
    if len(EXAMPLE_QUESTIONS) > 3:
        with st.expander("➕ More Questions", expanded=False):
            cols = st.columns(2)
            for i in range(3, len(EXAMPLE_QUESTIONS)):
                col = cols[(i - 3) % 2]
                with col:
                    question = EXAMPLE_QUESTIONS[i]
                    short_q = question[:40] + "..." if len(question) > 40 else question
                    if st.button(
                        short_q,
                        key=f"chip_more_{i}",
                        use_container_width=True,
                        help=question
                    ):
                        st.session_state["prefill"] = question
                        st.rerun()

    # Chat Interface
    st.divider()
    run_chat(deepseek_api_key)

# --- Tab 2: Housing Wizard ---
with tab2:
    if "vectorstore" not in st.session_state:
        st.warning("⚠️ Please load the knowledge base first from the sidebar.")
    else:
        # 标题和选项卡融合在一起
        st.caption("🏠 Housing Recommendation Wizard")
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            budget = st.selectbox(
                "💰 Budget",
                ["Budget-friendly", "Moderate", "Premium comfort"],
                index=0,
                key="wizard_budget"
            )

        with col_b:
            privacy = st.selectbox(
                "🚪 Privacy",
                ["Not important", "Nice to have", "Very important"],
                index=1,
                key="wizard_privacy"
            )

        with col_c:
            stay_term = st.selectbox(
                "📅 Duration",
                ["One semester", "Full academic year"],
                index=1,
                key="wizard_stay"
            )

        st.divider()

        if st.button("🎓 Generate Recommendations", type="primary", use_container_width=True):
            if not deepseek_api_key:
                st.error("❌ Enter API Key in sidebar first")
            else:
                with st.spinner("🤔 Generating personalized plan..."):
                    plan = generate_housing_plan(
                        {
                            "budget": budget,
                            "privacy": privacy,
                            "stay_term": stay_term,
                        },
                        deepseek_api_key,
                    )

                st.success("✅ Recommendations generated!")
                st.markdown("---")
                st.markdown(plan)

                # 保存到 session_state 以便反馈
                st.session_state["housing_plan"] = plan
                st.session_state["housing_preferences"] = {
                    "budget": budget,
                    "privacy": privacy,
                    "stay_term": stay_term,
                }

        # 显示反馈按钮（如果有生成的推荐）
        if "housing_plan" in st.session_state and st.session_state.get("housing_plan"):
            st.markdown("---")
            st.caption("Was this recommendation helpful?")

            # 检查是否已有反馈
            if "housing_feedback" not in st.session_state:
                st.session_state["housing_feedback"] = None

            if st.session_state["housing_feedback"] is None:
                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    if st.button("👍 Helpful", key="housing_fb_up"):
                        from utils import log_feedback
                        interaction = {
                            "question": f"Housing Wizard: {st.session_state.get('housing_preferences', {})}",
                            "answer": st.session_state["housing_plan"],
                            "used_rag": True,
                            "sources": ["Housing Wizard"],
                        }
                        if log_feedback("up", interaction):
                            st.session_state["housing_feedback"] = "up"
                            st.toast("Thank you for your feedback!", icon="👍")
                            st.rerun()
                with fb_col2:
                    if st.button("👎 Not Helpful", key="housing_fb_down"):
                        from utils import log_feedback
                        interaction = {
                            "question": f"Housing Wizard: {st.session_state.get('housing_preferences', {})}",
                            "answer": st.session_state["housing_plan"],
                            "used_rag": True,
                            "sources": ["Housing Wizard"],
                        }
                        if log_feedback("down", interaction):
                            st.session_state["housing_feedback"] = "down"
                            st.toast("Feedback recorded!", icon="👎")
                            st.rerun()
            else:
                if st.session_state["housing_feedback"] == "up":
                    st.caption("✅ You found this helpful")
                else:
                    st.caption("✅ Feedback recorded")

# --- Fixed Footer ---
st.markdown(
    """
    <style>
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: var(--background-color);
        border-top: 1px solid var(--border-color);
        padding: 0.5rem 1rem;
        text-align: center;
        font-size: 0.85rem;
        color: #666;
        z-index: 999;
    }
    /* Add padding to main content to prevent footer overlap */
    .main .block-container {
        padding-bottom: 3rem;
    }
    </style>
    <div class="fixed-footer">
        Made with ❤️ for NTU international graduate students | Powered by DeepSeek API
    </div>
    """,
    unsafe_allow_html=True
)
