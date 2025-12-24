"""
Chat UI utilities - scroll, message rendering, feedback buttons
"""
import streamlit as st
import streamlit.components.v1 as components

from utils import log_feedback


def scroll_to_bottom():
    """注入 JS 滚动到聊天底部"""
    components.html(
        """
        <script>
            setTimeout(function() {
                var chatBottom = window.parent.document.getElementById('chat-bottom');
                if (chatBottom) {
                    chatBottom.scrollIntoView({ behavior: 'smooth' });
                }
            }, 100);
        </script>
        """,
        height=0,
    )


def render_chat_anchor():
    """在聊天区底部放置锚点"""
    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)


def render_message_with_feedback(msg: dict, idx: int):
    """
    渲染单条消息及其反馈按钮

    Args:
        msg: 消息字典，包含 role, content, is_placeholder, used_rag, sources 等
        idx: 消息在列表中的索引
    """
    with st.chat_message(msg["role"]):
        # 检查是否是占位消息（正在生成中）
        if msg.get("is_placeholder"):
            st.caption("🔍 Searching knowledge base...")
        else:
            st.write(msg["content"])

        # 为每条助手消息添加反馈按钮（跳过欢迎消息和占位消息）
        if msg["role"] == "assistant" and idx > 0 and not msg.get("is_placeholder"):
            render_feedback_buttons(msg, idx)


def render_feedback_buttons(msg: dict, idx: int):
    """
    渲染反馈按钮

    Args:
        msg: 消息字典
        idx: 消息索引
    """
    # 检查是否已经有反馈记录
    feedback_key = f"feedback_{idx}"
    if feedback_key not in st.session_state:
        st.session_state[feedback_key] = None

    # 如果还没有反馈，显示按钮
    if st.session_state[feedback_key] is None:
        fb_col1, fb_col2 = st.columns(2)
        with fb_col1:
            if st.button("👍 Helpful", key=f"fb_up_{idx}"):
                # 从消息中提取问答信息
                question = st.session_state.messages[idx - 1]["content"] if idx > 0 else ""
                answer = msg["content"]
                interaction = {
                    "question": question,
                    "answer": answer,
                    "used_rag": msg.get("used_rag", False),
                    "sources": msg.get("sources", []),
                }
                if log_feedback("up", interaction):
                    st.session_state[feedback_key] = "up"
                    st.toast("Thank you for your feedback!", icon="👍")
                    st.rerun()
        with fb_col2:
            if st.button("👎 Not Helpful", key=f"fb_down_{idx}"):
                question = st.session_state.messages[idx - 1]["content"] if idx > 0 else ""
                answer = msg["content"]
                interaction = {
                    "question": question,
                    "answer": answer,
                    "used_rag": msg.get("used_rag", False),
                    "sources": msg.get("sources", []),
                }
                if log_feedback("down", interaction):
                    st.session_state[feedback_key] = "down"
                    st.toast("Feedback recorded!", icon="👎")
                    st.rerun()
    else:
        # 已经有反馈，显示状态
        if st.session_state[feedback_key] == "up":
            st.caption("✅ You found this helpful")
        else:
            st.caption("✅ Feedback recorded")


def render_chat_history(chat_area):
    """
    渲染聊天历史记录

    Args:
        chat_area: Streamlit container for chat messages
    """
    with chat_area:
        for idx, msg in enumerate(st.session_state.messages):
            # 跳过空的欢迎消息
            if not msg["content"].strip():
                continue
            render_message_with_feedback(msg, idx)

        # 在聊天区底部放置锚点
        render_chat_anchor()
