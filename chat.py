import streamlit as st

import os
import csv
import datetime

# 你的原始 import（未改）
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

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
                if hasattr(self.retriever, "get_relevant_documents"):
                    return self.retriever.get_relevant_documents(query)
                if hasattr(self.retriever, "get_relevant_source_documents"):
                    return self.retriever.get_relevant_source_documents(query)
                # some retrievers are callable
                try:
                    maybe = self.retriever(query)
                    # if returns list-like assume docs
                    return maybe
                except Exception:
                    return []

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
                    joined = "\n\n".join(getattr(d, "page_content", str(d)) for d in docs)
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
                result = self._call_doc_chain(docs, query)
                text = self._normalize_to_text(result)
                return {"answer": text, "source_documents": docs}

        return SimpleRAG(retriever, doc_chain)

# 你的原有 import（你之前文件里也有这行）
from langchain.chains.combine_documents import create_stuff_documents_chain

def _log_feedback(label, interaction):
    """
    简单把用户对最新回答的反馈写到本地 CSV：
    - label: "up" / "down"
    - interaction: 最近一次问答的信息（问题 / 回答 / 是否用了 RAG / 来源）
    """
    if not interaction:
        return

    try:
        row = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "label": label,
            "question": interaction.get("question", ""),
            "answer": interaction.get("answer", "")[:200],  # 截断一下避免太长
            "used_rag": interaction.get("used_rag", False),
            "sources": "|".join(interaction.get("sources") or []),
        }

        file_exists = os.path.exists("feedback_log.csv")
        fieldnames = list(row.keys())

        with open("feedback_log.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception:
        # demo 阶段，可以不打扰用户，静默失败即可
        pass



def run_chat(deepseek_api_key: str) -> None:
    # 1. 初始化会话 & 最近一次交互
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "你好！我是 NTU Campus Genie。"
                           "建议你先上传/构建宿舍 & STP 相关文档，然后可以直接问我问题，"
                           "或者点击上面的示例问题快速开始～",
            }
        ]
    if "last_interaction" not in st.session_state:
        st.session_state["last_interaction"] = None

    # 2. 展示历史消息
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # 3. 支持“预填问题”（从快速开始按钮来）+ 手动输入
    user_input = st.chat_input("请输入问题...")
    prompt = None

    # 如果上一步点击了“快速开始”按钮，就优先用 prefill
    prefill = st.session_state.get("prefill")
    if prefill:
        prompt = prefill
        st.session_state["prefill"] = ""
    elif user_input:
        prompt = user_input

    # 没有任何输入就直接返回
    if not prompt:
        return

    # 4. 没有 API Key 就提示并中断
    if not deepseek_api_key:
        st.info("请先在左侧设置 DeepSeek API Key。")
        st.stop()

    # 5. 把本轮用户消息加入历史并展示
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    try:
        # 初始化 LLM
        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1",
        )

        used_rag = False
        source_names = []

        # 6. 如果已经有向量知识库 → 使用 RAG
        if "vectorstore" in st.session_state:
            vectorstore = st.session_state["vectorstore"]
            retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

            prompt_tmpl = ChatPromptTemplate.from_template(
                """
                你是一个热心、专业的 NTU 校园助手。
                请基于以下【背景信息】回答用户的【问题】。
                如果不知道，请直接说“文档中未提及”。

                【背景信息】：
                {context}

                【问题】：
                {input}
                """
            )

            doc_chain = create_stuff_documents_chain(llm, prompt_tmpl)
            rag_chain = create_retrieval_chain(retriever, doc_chain)

            with st.chat_message("assistant"):
                st.caption("🔍 正在检索知识库...")
                response = rag_chain.invoke({"input": prompt})
                answer = response["answer"]

                # 从我们刚才在 SimpleRAG 里加的 source_documents 里整理来源
                docs = response.get("source_documents") or []
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
                    with st.expander("📎 参考来源 / Sources", expanded=False):
                        for name in source_names:
                            st.caption(f"- {name}")

            used_rag = True

        # 7. 如果还没有知识库，就退化为普通聊天
        else:
            with st.chat_message("assistant"):
                response = llm.invoke([HumanMessage(content=prompt)])
                answer = response.content
                st.write(answer)

        # 8. 把助手回答写入历史
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # 记录最近一次交互，方便写 feedback
        st.session_state["last_interaction"] = {
            "question": prompt,
            "answer": answer,
            "used_rag": used_rag,
            "sources": source_names,
        }

        # 9. 反馈按钮（只针对最新一轮回答）
        fb_col1, fb_col2 = st.columns(2)
        with fb_col1:
            if st.button("👍 有帮助", key=f"fb_up_{len(st.session_state.messages)}"):
                _log_feedback("up", st.session_state["last_interaction"])
                st.toast("感谢你的反馈！", icon="👍")
        with fb_col2:
            if st.button("👎 没帮助", key=f"fb_down_{len(st.session_state.messages)}"):
                _log_feedback("down", st.session_state["last_interaction"])
                st.toast("已记录你的反馈～", icon="👎")

    except Exception as e:
        st.error(f"发生错误: {e}")

