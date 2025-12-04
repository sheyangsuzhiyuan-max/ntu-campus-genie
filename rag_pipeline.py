import os
import tempfile
from typing import List, Dict, Any

import streamlit as st
# 引入 WebBaseLoader
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


def build_knowledge_base(
    uploaded_files,
    urls: List[str],  # ✅ 关键修正：这里必须有 urls 参数
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """
    从上传文件和 URL 构建向量知识库
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        all_documents = []
        file_stats: List[Dict[str, Any]] = []
        
        # 计算总任务数
        total_items = len(uploaded_files) + len(urls)
        if total_items == 0:
            st.warning("⚠️ 请至少上传一个文件或输入一个网址")
            return

        current_item = 0

        # === A. 处理上传的文件 ===
        if uploaded_files:
            for uploaded_file in uploaded_files:
                current_item += 1
                progress = current_item / (total_items + 1)
                progress_bar.progress(progress)
                status_text.text(f"📖 正在加载文件: {uploaded_file.name}")

                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_filepath = tmp_file.name
                
                try:
                    if uploaded_file.name.lower().endswith(".pdf"):
                        loader = PyPDFLoader(temp_filepath)
                    else:
                        loader = TextLoader(temp_filepath)
                    
                    docs = loader.load()
                    all_documents.extend(docs)
                    
                    file_stats.append({
                        "name": uploaded_file.name,
                        "type": "📄 文件",
                        "chars": sum(len(d.page_content) for d in docs)
                    })
                except Exception as e:
                    st.error(f"❌ 文件 {uploaded_file.name} 读取失败: {e}")
                finally:
                    if os.path.exists(temp_filepath):
                        os.unlink(temp_filepath)

        # === B. 处理 URL (带浏览器伪装) ===
        if urls:
            for url in urls:
                if not url.strip(): continue
                
                current_item += 1
                progress = current_item / (total_items + 1)
                progress_bar.progress(progress)
                status_text.text(f"🌐 正在爬取网页: {url}")

                try:
                    # 伪装成浏览器，防止 403 错误
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
                    }
                    loader = WebBaseLoader(url, header_template=headers)
                    docs = loader.load()
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

        status_text.text("✂️ 正在切分文档...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        split_docs = text_splitter.split_documents(all_documents)

        status_text.text("🔢 正在生成向量索引...")
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(split_docs, embeddings)

        st.session_state["vectorstore"] = vectorstore
        st.session_state["doc_stats"] = file_stats 
        
        progress_bar.empty()
        status_text.empty()
        st.success(f"✅ 知识库构建完成！共包含 {len(file_stats)} 个数据源。")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"构建过程发生未知错误: {e}")