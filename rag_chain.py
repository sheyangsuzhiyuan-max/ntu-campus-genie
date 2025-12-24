"""
RAG Chain utilities - create_retrieval_chain shim and rerank functions
"""
import streamlit as st

# 兼容 shim：若原函数存在就用原函数，否则定义一个与原用法兼容的实现
try:
    from langchain.chains import create_retrieval_chain  # type: ignore
except Exception:
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
