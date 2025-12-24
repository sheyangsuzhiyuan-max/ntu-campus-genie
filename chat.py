"""
Main chat functionality - run_chat entry point
"""
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

from config import (
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_URL,
    DEFAULT_RETRIEVAL_K,
    SYSTEM_PROMPT_CHAT,
    USE_RERANK,
    RERANK_TOP_K,
)
from utils import init_session_state
from rag_chain import rerank_documents
from chat_ui import scroll_to_bottom, render_chat_history

# Re-export for backward compatibility
from housing import generate_housing_plan  # noqa: F401


def run_chat(deepseek_api_key: str) -> None:
    """
    Main chat function with two-phase rerun for smooth scrolling.

    Phase A: On new input, immediately add placeholder message and rerun
    Phase B: Process the question, generate answer, update message and rerun
    """
    # 1. 初始化会话
    init_session_state()

    # 初始化状态
    if "pending_prompt" not in st.session_state:
        st.session_state["pending_prompt"] = None

    # 创建一个固定容器来放置所有对话内容
    chat_area = st.container()

    # 2. 展示历史消息（带反馈按钮）
    render_chat_history(chat_area)

    # 3. 获取用户输入
    user_input = st.chat_input("Type your question here...")
    prompt = None

    # Quick start button 优先
    prefill = st.session_state.get("prefill")
    if prefill:
        prompt = prefill
        st.session_state["prefill"] = ""
    elif user_input:
        prompt = user_input

    # ========== 阶段 A：收到新输入，立即写入占位消息并 rerun ==========
    if prompt and st.session_state["pending_prompt"] is None:
        # 检查 API Key
        if not deepseek_api_key:
            st.info("Please enter your DeepSeek API Key in the sidebar first.")
            st.stop()

        # 把用户消息和占位助手消息加入历史
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({
            "role": "assistant",
            "content": "",
            "is_placeholder": True,
        })
        st.session_state["pending_prompt"] = prompt
        scroll_to_bottom()
        st.rerun()

    # ========== 阶段 B：处理待处理的问题，生成真正的回答 ==========
    pending = st.session_state.get("pending_prompt")
    if pending:
        prompt = pending
        st.session_state["pending_prompt"] = None

        try:
            # 初始化 LLM
            llm = ChatOpenAI(
                model=DEEPSEEK_MODEL,
                openai_api_key=deepseek_api_key,
                base_url=DEEPSEEK_BASE_URL,
            )

            used_rag = False
            source_names = []

            # 如果有向量知识库 → 使用 RAG
            if "vectorstore" in st.session_state:
                answer, source_names = _generate_rag_answer(llm, prompt)
                used_rag = True
            else:
                # fallback to general chat
                response = llm.invoke([HumanMessage(content=prompt)])
                answer = response.content

            # 更新占位消息为真正的回答
            st.session_state.messages[-1] = {
                "role": "assistant",
                "content": answer,
                "used_rag": used_rag,
                "sources": source_names,
            }

            # Record last interaction
            st.session_state["last_interaction"] = {
                "question": prompt,
                "answer": answer,
                "used_rag": used_rag,
                "sources": source_names,
            }

            scroll_to_bottom()
            st.rerun()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.session_state.messages[-1] = {
                "role": "assistant",
                "content": f"Error occurred: {e}\n\nDetails:\n```\n{error_details}\n```",
                "used_rag": False,
                "sources": [],
            }
            st.rerun()


def _generate_rag_answer(llm, prompt: str) -> tuple[str, list]:
    """
    Generate answer using RAG pipeline.

    Returns:
        tuple of (answer_text, source_names_list)
    """
    vectorstore = st.session_state["vectorstore"]

    # Retrieve documents
    retriever = vectorstore.as_retriever(search_kwargs={"k": DEFAULT_RETRIEVAL_K})
    raw_docs = retriever.get_relevant_documents(prompt)

    # Ensure return value is a list
    if not isinstance(raw_docs, list):
        raw_docs = [raw_docs] if raw_docs else []

    # Filter valid documents
    retrieved_docs = [
        d for d in raw_docs if hasattr(d, "page_content") and hasattr(d, "metadata")
    ]

    # Rerank if enabled
    if USE_RERANK and len(retrieved_docs) > 0:
        docs = rerank_documents(prompt, retrieved_docs, top_k=RERANK_TOP_K)
    else:
        docs = retrieved_docs[:RERANK_TOP_K]

    # Final filter
    docs = [d for d in docs if hasattr(d, "page_content")]

    # Generate answer
    prompt_tmpl = ChatPromptTemplate.from_template(SYSTEM_PROMPT_CHAT)
    doc_chain = create_stuff_documents_chain(llm, prompt_tmpl)
    result = doc_chain.invoke({"context": docs, "input": prompt})

    if isinstance(result, dict):
        answer = result.get("output_text") or result.get("answer") or str(result)
    else:
        answer = str(result)

    # Extract sources
    source_names = []
    seen = set()
    for d in docs:
        src = None
        meta = getattr(d, "metadata", {}) or {}
        for key in ("source", "file_path", "url"):
            if meta.get(key):
                src = meta[key]
                break
        if not src:
            src = "Unknown source"
        if src not in seen:
            seen.add(src)
            source_names.append(src)

    return answer, source_names
