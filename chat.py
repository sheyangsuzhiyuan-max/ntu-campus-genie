import streamlit as st
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
                return {"answer": text}

        return SimpleRAG(retriever, doc_chain)

# 你的原有 import（你之前文件里也有这行）
from langchain.chains.combine_documents import create_stuff_documents_chain

# ---------- 下面保留你原来的函数体，未改逻辑，只是用上面的兼容 shim ----------
def run_chat(deepseek_api_key: str) -> None:
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "你好！我是你的 AI 助手。请上传文档并点击构建知识库，然后问我相关问题。"}
        ]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("请输入问题..."):
        if not deepseek_api_key:
            st.info("请先设置 API Key。")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        try:
            llm = ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
            )

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
                    st.write(answer)
            else:
                with st.chat_message("assistant"):
                    response = llm.invoke([HumanMessage(content=prompt)])
                    answer = response.content
                    st.write(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            st.error(f"发生错误: {e}")
