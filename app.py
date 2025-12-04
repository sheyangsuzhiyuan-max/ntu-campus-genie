import os
import subprocess
import sys

# 暴力补丁：如果环境缺包，直接在运行代码时强制安装
try:
    import bs4
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])

import streamlit as st
from rag_pipeline import build_knowledge_base
from chat import run_chat

# --- 1. 页面基础设置 ---
st.set_page_config(page_title="NTU Genie", page_icon="🏫", layout="wide")
st.title("🏫 NTU Campus Genie")

# --- 2. 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 设置")
    
    # API Key 输入
    deepseek_api_key = st.text_input("DeepSeek API Key", type="password")
    st.markdown("[🔗 获取 Key](https://platform.deepseek.com/api-keys)")
    
    st.divider()
    
    st.subheader("📚 知识库构建")
    
    # Tab 页切换：让界面更整洁
    tab1, tab2 = st.tabs(["📄 上传文件", "🌐 输入网址"])
    
    with tab1:
        uploaded_files = st.file_uploader(
            "选择 PDF 或 TXT", 
            type=["pdf", "txt"], 
            accept_multiple_files=True
        )
    
    with tab2:
        url_input = st.text_area(
            "输入 NTU 网页链接 (每行一个)", 
            height=100,
            value="https://www.ntu.edu.sg/about-us/ntu2025\nhttps://www.ntu.edu.sg/life-at-ntu/accommodation",
            help="提示：某些需要登录的页面无法抓取"
        )
        # 处理 URL 输入，去除空行
        urls = [line.strip() for line in url_input.split('\n') if line.strip()]

    # 只要有文件或 URL，就显示构建按钮
    if uploaded_files or urls:
        st.info(f"待处理: {len(uploaded_files)} 个文件, {len(urls)} 个网址")
        
        if st.button("🔄 点击构建知识库", type="primary"):
            if not deepseek_api_key:
                st.error("❌ 请先输入 API Key！")
            else:
                # 调用后端处理
                build_knowledge_base(
                    uploaded_files=uploaded_files,
                    urls=urls,
                    chunk_size=1000,
                    chunk_overlap=200
                )
    
    # 展示已构建的数据源统计 (如果有的话)
    if "doc_stats" in st.session_state:
        st.divider()
        st.caption("📊 当前知识库包含：")
        for stat in st.session_state["doc_stats"]:
            st.caption(f"- {stat['name']} ({stat['chars']} 字)")

# --- 3. 聊天主逻辑 ---
run_chat(deepseek_api_key)