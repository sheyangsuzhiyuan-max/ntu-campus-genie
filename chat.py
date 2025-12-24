import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from config import (
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_URL,
    DEFAULT_RETRIEVAL_K,
    SYSTEM_PROMPT_CHAT,
    SYSTEM_PROMPT_HOUSING,
    USE_RERANK,
    RERANK_TOP_K,
)
from utils import log_feedback, get_unique_button_key, init_session_state

# 原本直接从 langchain.chains import create_retrieval_chain 会在部分版本中报错
# 我们用兼容 shim：若原函数存在就用原函数，否则定义一个与原用法兼容的实现
try:
    from langchain.chains import create_retrieval_chain  # type: ignore
except Exception:
    # 兼容实现：接收 (retriever, doc_chain) 并返回有 .invoke(inputs) 的对象
    from langchain.chains.combine_documents import create_stuff_documents_chain  # 保留引用位置（你的代码也单独 import 了）
    import logging

    logging.info("create_retrieval_chain not found — using local shim")

    def create_retrieval_chain(retriever, doc_chain, **kwargs):
        """
        Shim for older/newer langchain API differences.

        Expected call in your code:
            rag_chain = create_retrieval_chain(retriever, doc_chain)
            response = rag_chain.invoke({"input": prompt})
            answer = response["answer"]

        This shim:
          - uses retriever.get_relevant_documents(query) (or falls back to other call patterns)
          - calls doc_chain with {"input_documents": docs, "input": query}
          - attempts to normalize the result and returns {"answer": text}
        """
        class SimpleRAG:
            def __init__(self, retriever, doc_chain):
                self.retriever = retriever
                self.doc_chain = doc_chain

            def _get_documents(self, query):
                # Common getter names across vectorstores/retrievers
                raw_docs = []
                if hasattr(self.retriever, "get_relevant_documents"):
                    raw_docs = self.retriever.get_relevant_documents(query)
                elif hasattr(self.retriever, "get_relevant_source_documents"):
                    raw_docs = self.retriever.get_relevant_source_documents(query)
                else:
                    # some retrievers are callable
                    try:
                        raw_docs = self.retriever(query)
                    except Exception:
                        raw_docs = []

                # 确保返回的是列表
                if not isinstance(raw_docs, list):
                    raw_docs = [raw_docs] if raw_docs else []

                # 过滤掉非 Document 对象，只保留有 page_content 属性的对象
                return [d for d in raw_docs if hasattr(d, "page_content")]

            def _call_doc_chain(self, docs, query):
                inputs = {"input_documents": docs, "input": query}
                # prefer invoke
                if hasattr(self.doc_chain, "invoke"):
                    try:
                        return self.doc_chain.invoke(inputs)
                    except TypeError:
                        # some chains expect positional args or different signature — try other options
                        pass
                # try run
                if hasattr(self.doc_chain, "run"):
                    try:
                        return self.doc_chain.run(input_documents=docs, input=query)
                    except TypeError:
                        try:
                            return self.doc_chain.run(query)
                        except Exception:
                            pass
                # if callable, call with inputs
                if callable(self.doc_chain):
                    try:
                        return self.doc_chain(inputs)
                    except Exception:
                        pass
                # fallback: return joined docs text
                try:
                    # 确保 docs 都有 page_content 属性
                    valid_docs = [d for d in docs if hasattr(d, "page_content")]
                    joined = "\n\n".join(d.page_content for d in valid_docs)
                    return {"output_text": joined}
                except Exception:
                    return {"output_text": ""}

            def _normalize_to_text(self, result):
                # result can be dict, str, or other
                if isinstance(result, str):
                    return result
                if isinstance(result, dict):
                    for k in ("answer", "output_text", "text", "output"):
                        if k in result:
                            # if nested structures, coerce to str
                            val = result[k]
                            return val if isinstance(val, str) else str(val)
                    # fallback: first string value
                    for v in result.values():
                        if isinstance(v, str):
                            return v
                    return str(result)
                return str(result)

            def invoke(self, inputs: dict):
                # expects inputs like {"input": "user question"}
                query = inputs.get("input") or inputs.get("query") or ""
                docs = self._get_documents(query) or []

                # 再次确保所有 docs 都有 page_content（防御性编程）
                docs = [d for d in docs if hasattr(d, "page_content")]

                result = self._call_doc_chain(docs, query)
                text = self._normalize_to_text(result)
                return {"answer": text, "source_documents": docs}

        return SimpleRAG(retriever, doc_chain)

# 你的原有 import（你之前文件里也有这行）
from langchain.chains.combine_documents import create_stuff_documents_chain


def rerank_documents(query: str, documents: list, top_k: int = 3):
    """
    使用 FlashRank 对检索到的文档进行重排序

    Args:
        query: 用户查询
        documents: 检索到的文档列表
        top_k: 保留前 k 个文档

    Returns:
        重排序后的文档列表
    """
    # 确保 documents 是列表
    if not isinstance(documents, list):
        documents = [documents] if documents else []

    # 过滤掉没有 page_content 的条目，避免后续 AttributeError
    clean_docs = [d for d in documents if hasattr(d, "page_content") and hasattr(d, "metadata")]
    if not clean_docs:
        return []

    try:
        from flashrank import Ranker, RerankRequest

        ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp")

        passages = []
        for i, doc in enumerate(clean_docs):
            passages.append(
                {
                    "id": i,
                    "text": getattr(doc, "page_content", ""),
                    "meta": getattr(doc, "metadata", {}),
                }
            )

        rerank_request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(rerank_request)

        reranked_docs = []
        for result in results[:top_k]:
            doc_id = result["id"]
            if 0 <= doc_id < len(clean_docs):
                reranked_docs.append(clean_docs[doc_id])

        return reranked_docs
    except Exception as e:
        # 如果 rerank 失败，返回原始文档
        st.warning(f"⚠️ Rerank 失败，使用原始检索结果: {e}")
        return clean_docs[:top_k]


def run_chat(deepseek_api_key: str) -> None:
    # 1. 初始化会话 & 最近一次交互
    init_session_state()

    # 2. 展示历史消息（带反馈按钮）
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

            # 为每条助手消息添加反馈按钮（跳过欢迎消息）
            if msg["role"] == "assistant" and idx > 0:
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

    # 3. Support "prefilled questions" (from quick start buttons) + manual input
    user_input = st.chat_input("Type your question here...")
    prompt = None

    # If "quick start" button was clicked, use prefill first
    prefill = st.session_state.get("prefill")
    if prefill:
        prompt = prefill
        st.session_state["prefill"] = ""
    elif user_input:
        prompt = user_input

    # Return if no input
    if not prompt:
        return

    # 4. Prompt and stop if no API Key
    if not deepseek_api_key:
        st.info("Please enter your DeepSeek API Key in the sidebar first.")
        st.stop()

    # 5. 把本轮用户消息加入历史并展示
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    try:
        # 初始化 LLM
        llm = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            openai_api_key=deepseek_api_key,
            base_url=DEEPSEEK_BASE_URL,
        )

        used_rag = False
        source_names = []

        # 6. 如果已经有向量知识库 → 使用 RAG
        if "vectorstore" in st.session_state:
            vectorstore = st.session_state["vectorstore"]

            with st.chat_message("assistant"):
                st.caption("🔍 Searching knowledge base...")

                # Retrieve documents first
                retriever = vectorstore.as_retriever(search_kwargs={"k": DEFAULT_RETRIEVAL_K})
                raw_docs = retriever.get_relevant_documents(prompt)

                # Ensure return value is a list
                if not isinstance(raw_docs, list):
                    raw_docs = [raw_docs] if raw_docs else []

                # Filter out non-Document objects to avoid missing attributes
                retrieved_docs = [
                    d for d in raw_docs if hasattr(d, "page_content") and hasattr(d, "metadata")
                ]

                # If rerank is enabled, reorder the retrieved documents
                if USE_RERANK and len(retrieved_docs) > 0:
                    st.caption("🎯 Optimizing results (Rerank)...")
                    docs = rerank_documents(prompt, retrieved_docs, top_k=RERANK_TOP_K)
                else:
                    docs = retrieved_docs[:RERANK_TOP_K]

                # 最终再防御一次：只保留具备 page_content 的文档
                docs = [d for d in docs if hasattr(d, "page_content")]

                # 使用 rerank 后的文档生成答案
                prompt_tmpl = ChatPromptTemplate.from_template(SYSTEM_PROMPT_CHAT)
                doc_chain = create_stuff_documents_chain(llm, prompt_tmpl)

                # ✅ 修复：doc_chain 期望的是 Document 对象列表，而不是字符串
                # 正确的调用方式是传递 Document 对象列表
                result = doc_chain.invoke({"context": docs, "input": prompt})

                if isinstance(result, dict):
                    answer = result.get("output_text") or result.get("answer") or str(result)
                else:
                    answer = str(result)

                # 整理来源（防御：确保有 metadata）
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

                st.write(answer)

                if source_names:
                    with st.expander("📎 Reference Sources", expanded=False):
                        for name in source_names:
                            st.caption(f"- {name}")

                # 新回答的反馈按钮（立即显示）
                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    if st.button("👍 Helpful", key=f"fb_up_new_{len(st.session_state.messages)}"):
                        interaction = {
                            "question": prompt,
                            "answer": answer,
                            "used_rag": True,
                            "sources": source_names,
                        }
                        if log_feedback("up", interaction):
                            # 保存反馈状态
                            next_idx = len(st.session_state.messages) + 1
                            st.session_state[f"feedback_{next_idx}"] = "up"
                            st.toast("Thank you for your feedback!", icon="👍")
                            st.rerun()
                with fb_col2:
                    if st.button("👎 Not Helpful", key=f"fb_down_new_{len(st.session_state.messages)}"):
                        interaction = {
                            "question": prompt,
                            "answer": answer,
                            "used_rag": True,
                            "sources": source_names,
                        }
                        if log_feedback("down", interaction):
                            next_idx = len(st.session_state.messages) + 1
                            st.session_state[f"feedback_{next_idx}"] = "down"
                            st.toast("Feedback recorded!", icon="👎")
                            st.rerun()

            used_rag = True

        # 7. If no knowledge base, fallback to general chat
        else:
            with st.chat_message("assistant"):
                response = llm.invoke([HumanMessage(content=prompt)])
                answer = response.content
                st.write(answer)

                # 新回答的反馈按钮（立即显示 - 非RAG模式）
                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    if st.button("👍 Helpful", key=f"fb_up_new_{len(st.session_state.messages)}"):
                        interaction = {
                            "question": prompt,
                            "answer": answer,
                            "used_rag": False,
                            "sources": [],
                        }
                        if log_feedback("up", interaction):
                            next_idx = len(st.session_state.messages) + 1
                            st.session_state[f"feedback_{next_idx}"] = "up"
                            st.toast("Thank you for your feedback!", icon="👍")
                            st.rerun()
                with fb_col2:
                    if st.button("👎 Not Helpful", key=f"fb_down_new_{len(st.session_state.messages)}"):
                        interaction = {
                            "question": prompt,
                            "answer": answer,
                            "used_rag": False,
                            "sources": [],
                        }
                        if log_feedback("down", interaction):
                            next_idx = len(st.session_state.messages) + 1
                            st.session_state[f"feedback_{next_idx}"] = "down"
                            st.toast("Feedback recorded!", icon="👎")
                            st.rerun()

        # 8. Add assistant response to history（保存 used_rag 和 sources 信息）
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "used_rag": used_rag,
            "sources": source_names,
        })

        # Record last interaction for feedback (保留以便兼容其他可能的用途)
        st.session_state["last_interaction"] = {
            "question": prompt,
            "answer": answer,
            "used_rag": used_rag,
            "sources": source_names,
        }

        # 注意：反馈按钮现在在历史消息展示部分（第193-242行），每条消息都有独立的按钮

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error occurred: {e}")
        with st.expander("🐛 View Detailed Error (Debug)"):
            st.code(error_details)


def generate_housing_plan(preferences: dict, deepseek_api_key: str) -> str:
    """
    Generate housing recommendations based on user preferences and knowledge base.
    preferences example:
    {
        "budget": "Budget-friendly",
        "privacy": "Very important",
        "stay_term": "Full academic year (2 semesters)",
    }
    """
    if "vectorstore" not in st.session_state:
        return "No housing knowledge base found. Please upload documents or enter NTU webpage URLs to build the knowledge base first."

    if not deepseek_api_key:
        return "DeepSeek API Key not set. Please enter it in the sidebar first."

    # 初始化 LLM
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        openai_api_key=deepseek_api_key,
        base_url=DEEPSEEK_BASE_URL,
    )

    vectorstore = st.session_state["vectorstore"]
    retriever = vectorstore.as_retriever(search_kwargs={"k": DEFAULT_RETRIEVAL_K})

    # 把偏好转成一段自然语言描述，作为检索查询
    pref_text = (
        f"预算倾向：{preferences.get('budget')}\n"
        f"隐私 / 独立卫生间：{preferences.get('privacy')}\n"
        f"预计入住时长：{preferences.get('stay_term')}\n"
    )

    # 使用带偏好信息的 prompt 模板 - 注意：SYSTEM_PROMPT_HOUSING 需要 preferences, context, input 三个参数
    # 但 create_stuff_documents_chain 只支持 context 和 input，所以我们需要手动处理

    # Solution: Embed preferences into input, use simplified prompt
    simplified_prompt = """
You are an expert assistant familiar with NTU graduate housing.
Below are a student's housing preferences. Please provide recommendations based on the [Context Information].

Required output structure (respond in both English and Chinese):
1. Summarize their needs in 2-3 sentences (both in English and Chinese)
2. Recommend 1-2 specific housing options (e.g., Graduate Hall 1 twin sharing / North Hill single room),
   explaining why they are suitable (considering price, room type, private bathroom, etc.)
3. Provide a clear application checklist with bullet points, including:
   - When to submit the application in the system
   - Fees to pay (if mentioned in documents)
   - Important dates to check for housing results
If certain details are not mentioned in the documents, please clearly state "Not mentioned in the documents".

Please respond in both English and Chinese (中英双语回答).

[Context Information]:
{context}

[Question]:
{input}
"""

    try:
        prompt_tmpl = ChatPromptTemplate.from_template(simplified_prompt)
        doc_chain = create_stuff_documents_chain(llm, prompt_tmpl)
        rag_chain = create_retrieval_chain(retriever, doc_chain)

        # Pass preferences as input
        query = f"Based on the following preferences, recommend suitable housing:\n{pref_text}\nPlease provide a detailed housing recommendation plan."
        result = rag_chain.invoke({"input": query})
        answer = result.get("answer") or "Failed to generate recommendations. Please try again."

        return answer
    except Exception as e:
        import traceback
        error_msg = f"Error generating housing recommendations: {e}\n\nDetails:\n{traceback.format_exc()}"
        return error_msg
