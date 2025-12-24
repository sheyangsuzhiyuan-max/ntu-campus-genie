import streamlit as st

from rag_pipeline import build_knowledge_base
from chat import run_chat, generate_housing_plan
from utils import get_feedback_stats, init_session_state
from config import EXAMPLE_QUESTIONS, DEFAULT_URLS, DEFAULT_API_KEY

# --- 1. Page Configuration ---
st.set_page_config(page_title="NTU Genie", page_icon="🏫", layout="wide")

# Initialize session state
init_session_state()

st.title("🏫 NTU Campus Genie")
st.caption("Your AI-Powered NTU Campus Assistant - Graduate Housing & Visa Information")

# --- 2. Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")

    # API Key Input
    deepseek_api_key = st.text_input(
        "DeepSeek API Key",
        value=DEFAULT_API_KEY or "",
        type="password",
        help="Enter your DeepSeek API Key. Note: Do not use in public environments!"
    )

    if DEFAULT_API_KEY:
        st.success("✅ Demo API Key loaded (for testing)")
    else:
        st.markdown("[🔗 Get API Key](https://platform.deepseek.com/api-keys)")

    st.divider()

    st.subheader("📚 Knowledge Base Setup")

    # Quick Start Button
    if st.button("🚀 Quick Start: Load Default KB", type="primary", use_container_width=True):
        if not deepseek_api_key:
            st.error("❌ Please enter API Key first!")
        else:
            with st.spinner("Loading default knowledge base..."):
                build_knowledge_base(use_default_files=True)

    st.caption("💡 Includes: Housing & Visa guides")

    st.divider()

    # Simplified: Combined upload interface
    with st.expander("📁 Upload Custom Documents", expanded=False):
        tab1, tab2 = st.tabs(["📄 Files", "🌐 URLs"])

        with tab1:
            uploaded_files = st.file_uploader(
                "Select PDF or TXT",
                type=["pdf", "txt"],
                accept_multiple_files=True,
                help="Upload your own documents"
            )

        with tab2:
            url_input = st.text_area(
                "Enter URLs (one per line)",
                height=80,
                value="\n".join(DEFAULT_URLS),
                help="Pages requiring login cannot be scraped"
            )
            urls = [line.strip() for line in url_input.split('\n') if line.strip()]

        # Build button
        if uploaded_files or urls:
            st.info(f"📦 {len(uploaded_files)} file(s), {len(urls)} URL(s)")
            if st.button("🔄 Build KB", use_container_width=True):
                if not deepseek_api_key:
                    st.error("❌ Enter API Key first!")
                else:
                    build_knowledge_base(uploaded_files=uploaded_files, urls=urls)

    # Display KB status
    if "doc_stats" in st.session_state and st.session_state["doc_stats"]:
        st.divider()
        st.success("✅ KB Ready")
        with st.expander("📊 Data Sources", expanded=False):
            for stat in st.session_state["doc_stats"]:
                st.caption(f"• {stat['type']} **{stat['name']}** ({stat['chars']:,} chars)")

# --- 3. Main Content Area ---

# Top bar with Housing Wizard button
col1, col2 = st.columns([4, 1])
with col1:
    # Knowledge base status prompt
    if "vectorstore" not in st.session_state:
        st.info("💡 **Quick Start**: Click 'Quick Start: Load Default KB' in the sidebar to start chatting!")
with col2:
    # Housing Wizard Button (always visible)
    if st.button("🏠 Housing Wizard", use_container_width=True, type="secondary"):
        st.session_state["show_housing_wizard"] = True

# Housing Wizard Dialog (as a prominent section when activated)
if st.session_state.get("show_housing_wizard", False):
    with st.container():
        st.markdown("---")
        st.markdown("### 🏠 Graduate Housing Recommendation Wizard")

        if "vectorstore" not in st.session_state:
            st.warning("⚠️ Please load the knowledge base first to use the Housing Wizard.")
            st.info("Click 'Quick Start: Load Default KB' in the sidebar to get started.")
            if st.button("Close", key="close_wizard_no_kb"):
                st.session_state["show_housing_wizard"] = False
                st.rerun()
        else:
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                budget = st.selectbox(
                    "💰 Budget Preference",
                    ["Budget-friendly", "Moderate", "Premium comfort"],
                    index=0,
                    key="wizard_budget"
                )

            with col_b:
                privacy = st.selectbox(
                    "🚪 Privacy / Private Bathroom",
                    ["Not important", "Nice to have", "Very important"],
                    index=1,
                    key="wizard_privacy"
                )

            with col_c:
                stay_term = st.selectbox(
                    "📅 Stay Duration",
                    ["One semester", "Full academic year (2 semesters)"],
                    index=1,
                    key="wizard_stay"
                )

            button_col1, button_col2 = st.columns([3, 1])
            with button_col1:
                if st.button("🎓 Generate Housing Recommendations", type="primary", use_container_width=True):
                    if not deepseek_api_key:
                        st.error("❌ Please enter your DeepSeek API Key in the sidebar first")
                    else:
                        with st.spinner("🤔 Generating personalized housing plan..."):
                            plan = generate_housing_plan(
                                {
                                    "budget": budget,
                                    "privacy": privacy,
                                    "stay_term": stay_term,
                                },
                                deepseek_api_key,
                            )

                        st.markdown("#### 📋 Your Personalized Housing Plan")
                        st.markdown(plan)

            with button_col2:
                if st.button("✖ Close", use_container_width=True):
                    st.session_state["show_housing_wizard"] = False
                    st.rerun()

        st.markdown("---")

# --- Quick Start Example Questions ---
st.subheader("✨ Quick Start")

# Use column layout to display example questions
cols = st.columns(2)
for i, question in enumerate(EXAMPLE_QUESTIONS):
    col = cols[i % 2]
    with col:
        if st.button(
            f"💬 {question}",
            key=f"example_{i}",
            use_container_width=True,
            help="Click to ask this question"
        ):
            st.session_state["prefill"] = question
            st.rerun()

# --- Chat Main Logic ---
st.divider()
st.subheader("💬 AI Chat Assistant")
run_chat(deepseek_api_key)

# --- Usage Analytics ---
st.divider()
with st.expander("📈 Usage Statistics (Development)", expanded=False):
    stats = get_feedback_stats()

    if stats["total"] == 0:
        st.caption("No feedback data yet. Click 👍 or 👎 below each response to provide feedback.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Feedback", stats["total"])
        with col2:
            st.metric("👍 Helpful", stats["ups"])
        with col3:
            st.metric("👎 Not Helpful", stats["downs"])

        if stats["recent"]:
            st.caption("**Recent 5 Feedbacks:**")
            for r in stats["recent"]:
                q = (r.get("question") or "")[:80]
                used_rag = r.get("used_rag")
                st.caption(
                    f"• **Q**: {q}... | RAG: `{used_rag}` | Rating: `{r.get('label')}`"
                )

        # Download feedback data
        import os
        from config import FEEDBACK_LOG_FILE
        if os.path.exists(FEEDBACK_LOG_FILE):
            with open(FEEDBACK_LOG_FILE, "r", encoding="utf-8") as f:
                csv_data = f.read()
            st.download_button(
                label="📥 Download Feedback Data (CSV)",
                data=csv_data,
                file_name="ntu_genie_feedback.csv",
                mime="text/csv",
                use_container_width=True
            )

# --- Footer ---
st.divider()
st.caption("Made with ❤️ for NTU international graduate students | Powered by DeepSeek API")
