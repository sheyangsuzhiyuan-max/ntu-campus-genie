import os
import tempfile
from typing import List, Dict, Any, Optional

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from config import (
    EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_KNOWLEDGE_FILES,
)


def build_knowledge_base(
    uploaded_files=None,
    urls: Optional[List[str]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    use_default_files: bool = False,
) -> None:
    """
    从上传文件、URL 或默认文件构建向量知识库

    Args:
        uploaded_files: Streamlit 上传的文件列表
        urls: 要爬取的 URL 列表
        chunk_size: 文档切分大小
        chunk_overlap: 文档切分重叠
        use_default_files: 是否使用 data/ 目录下的默认文件
    """
    # 初始化参数
    uploaded_files = uploaded_files or []
    urls = urls or []

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        all_documents = []
        file_stats: List[Dict[str, Any]] = []

        # === 加载默认文件 ===
        default_files = []
        if use_default_files:
            for file_path in DEFAULT_KNOWLEDGE_FILES:
                if os.path.exists(file_path):
                    default_files.append(file_path)
                else:
                    st.warning(f"⚠️ 默认文件不存在: {file_path}")

        # 计算总任务数
        total_items = len(uploaded_files) + len(urls) + len(default_files)
        if total_items == 0:
            st.warning("⚠️ 请至少上传一个文件、输入一个网址或加载默认知识库")
            return

        current_item = 0

        # === A0. 处理默认文件 ===
        if default_files:
            for file_path in default_files:
                current_item += 1
                progress = current_item / (total_items + 1)
                progress_bar.progress(progress)
                status_text.text(f"📖 Loading default file: {os.path.basename(file_path)}")

                try:
                    if file_path.lower().endswith(".pdf"):
                        loader = PyPDFLoader(file_path)
                    else:
                        loader = TextLoader(file_path, encoding="utf-8")

                    docs = loader.load()

                    # 调试：打印加载结果的类型
                    # st.write(f"DEBUG: 加载 {os.path.basename(file_path)}, 类型: {type(docs)}, 是列表: {isinstance(docs, list)}")

                    # 确保 docs 是列表且所有元素都有 page_content 属性
                    if not isinstance(docs, list):
                        docs = [docs] if docs else []

                    # 过滤并记录问题文档
                    valid_docs = []
                    for i, d in enumerate(docs):
                        if hasattr(d, "page_content"):
                            valid_docs.append(d)
                        else:
                            st.warning(f"⚠️ 文件 {os.path.basename(file_path)} 的第 {i} 个文档不是标准格式（类型: {type(d)}），已跳过")

                    docs = valid_docs
                    if not docs:
                        st.warning(f"⚠️ 文件 {os.path.basename(file_path)} 没有提取到有效文档")
                        continue

                    all_documents.extend(docs)

                    file_stats.append({
                        "name": os.path.basename(file_path),
                        "type": "📄 默认文件",
                        "chars": sum(len(d.page_content) for d in docs)
                    })
                except Exception as e:
                    st.error(f"❌ 默认文件 {file_path} 读取失败: {e}")
                    continue

        # === A. 处理上传的文件 ===
        if uploaded_files:
            for uploaded_file in uploaded_files:
                current_item += 1
                progress = current_item / (total_items + 1)
                progress_bar.progress(progress)
                status_text.text(f"📖 Loading file: {uploaded_file.name}")

                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_filepath = tmp_file.name
                
                try:
                    if uploaded_file.name.lower().endswith(".pdf"):
                        loader = PyPDFLoader(temp_filepath)
                    else:
                        loader = TextLoader(temp_filepath, encoding="utf-8")

                    docs = loader.load()

                    # 确保 docs 是列表且所有元素都有 page_content 属性
                    if not isinstance(docs, list):
                        docs = [docs] if docs else []

                    # 过滤并记录问题文档
                    valid_docs = []
                    for i, d in enumerate(docs):
                        if hasattr(d, "page_content"):
                            valid_docs.append(d)
                        else:
                            st.warning(f"⚠️ 文件 {uploaded_file.name} 的第 {i} 个文档不是标准格式（类型: {type(d)}），已跳过")

                    docs = valid_docs
                    if not docs:
                        st.warning(f"⚠️ 文件 {uploaded_file.name} 没有提取到有效文档")
                        continue

                    all_documents.extend(docs)

                    file_stats.append({
                        "name": uploaded_file.name,
                        "type": "📄 上传文件",
                        "chars": sum(len(d.page_content) for d in docs)
                    })
                except Exception as e:
                    st.error(f"❌ 文件 {uploaded_file.name} 读取失败: {e}")
                    continue
                finally:
                    if os.path.exists(temp_filepath):
                        try:
                            os.unlink(temp_filepath)
                        except Exception:
                            pass  # 静默处理清理失败

        # === B. 处理 URL (带浏览器伪装) ===
        if urls:
            for url in urls:
                if not url.strip(): continue
                
                current_item += 1
                progress = current_item / (total_items + 1)
                progress_bar.progress(progress)
                status_text.text(f"🌐 Scraping webpage: {url}")

                try:
                    # 伪装成浏览器，防止 403 错误
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
                    }
                    loader = WebBaseLoader(url, header_template=headers)
                    docs = loader.load()

                    # 确保 docs 是列表且所有元素都有 page_content 属性
                    if not isinstance(docs, list):
                        docs = [docs] if docs else []

                    # 过滤并记录问题文档
                    valid_docs = []
                    for i, d in enumerate(docs):
                        if hasattr(d, "page_content"):
                            valid_docs.append(d)
                        else:
                            st.warning(f"⚠️ 网页 {url} 的第 {i} 个文档不是标准格式（类型: {type(d)}），已跳过")

                    docs = valid_docs
                    if not docs:
                        st.warning(f"⚠️ 网页 {url} 没有提取到有效文档")
                        continue

                    all_documents.extend(docs)

                    file_stats.append({
                        "name": url,
                        "type": "🌐 网页",
                        "chars": sum(len(d.page_content) for d in docs)
                    })
                except Exception as e:
                    st.warning(f"⚠️ 网页爬取失败 ({url}): {e}")
                    continue

        # === C. 切分与向量化 ===
        if not all_documents:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ 未提取到有效文本")
            return

        # 最后一次检查：确保所有文档都是有效的
        status_text.text("🔍 Validating documents...")
        valid_all_documents = []
        for i, doc in enumerate(all_documents):
            if hasattr(doc, "page_content"):
                valid_all_documents.append(doc)
            else:
                st.warning(f"⚠️ 检测到第 {i} 个文档格式异常（类型: {type(doc)}），已跳过")

        if not valid_all_documents:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ 所有文档都不是有效格式")
            return

        all_documents = valid_all_documents

        status_text.text("✂️ Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        split_docs = text_splitter.split_documents(all_documents)

        # 验证切分后的文档
        status_text.text("🔍 Validating chunks...")
        valid_split_docs = []
        for i, doc in enumerate(split_docs):
            if hasattr(doc, "page_content"):
                valid_split_docs.append(doc)
            else:
                st.warning(f"⚠️ 切分后第 {i} 个文档格式异常（类型: {type(doc)}），已跳过")

        if not valid_split_docs:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ 切分后没有有效文档")
            return

        split_docs = valid_split_docs

        status_text.text("🔢 Generating vector index (first run may download model, please wait)...")
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vectorstore = FAISS.from_documents(split_docs, embeddings)

        st.session_state["vectorstore"] = vectorstore
        st.session_state["doc_stats"] = file_stats 
        
        progress_bar.empty()
        status_text.empty()
        st.success(f"✅ 知识库构建完成！共包含 {len(file_stats)} 个数据源。")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ 构建过程发生错误: {e}")
        st.exception(e)  # 显示完整错误堆栈，便于调试
