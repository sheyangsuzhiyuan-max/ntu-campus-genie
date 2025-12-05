import os
import csv

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

# --- 知识库统计 ---
if "doc_stats" in st.session_state:
    st.divider()
    st.caption("📊 当前知识库包含：")
    for stat in st.session_state["doc_stats"]:
        st.caption(f"- {stat['type']} {stat['name']} ({stat['chars']} 字)")


# --- 快速开始问题 ---
st.divider()
st.subheader("✨ 快速开始（示例问题）")
# ... 你已有的示例按钮代码 ...

# --- 宿舍申请向导 ---
st.divider()
st.subheader("🏠 研究生宿舍申请向导")

if "vectorstore" not in st.session_state:
    st.info("请先上传宿舍相关文档或输入 NTU 官网链接，并点击左侧的『点击构建知识库』。")
else:
    with st.expander("根据你的偏好生成宿舍推荐与申请计划", expanded=False):
        budget = st.selectbox(
            "你的预算倾向是？",
            ["尽量省钱", "中等预算", "可以接受更贵但更舒适"],
            index=0,
        )
        privacy = st.selectbox(
            "你对隐私 / 独立卫生间的重视程度？",
            ["不太在意", "有就更好", "非常在意"],
            index=1,
        )
        stay_term = st.selectbox(
            "计划住宿时间：",
            ["单学期", "整学年（2 学期）"],
            index=1,
        )

        if st.button("生成宿舍推荐与申请计划", key="btn_housing_plan"):
            # 避免顶部循环 import，这里在本地导入
            from chat import generate_housing_plan

            with st.spinner("正在根据你的偏好生成方案..."):
                plan = generate_housing_plan(
                    {
                        "budget": budget,
                        "privacy": privacy,
                        "stay_term": stay_term,
                    },
                    deepseek_api_key,
                )

            st.markdown(plan)

# --- 聊天主逻辑 ---
run_chat(deepseek_api_key)

# --- 简单使用数据 / 实验分析 ---
st.divider()
with st.expander("📈 简单使用数据（本地调试用）", expanded=False):
    if not os.path.exists("feedback_log.csv"):
        st.caption("目前还没有任何反馈数据。可以在每次回答下面点 👍 或 👎 来记录反馈。")
    else:
        rows = []
        with open("feedback_log.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total = len(rows)
        ups = sum(1 for r in rows if r.get("label") == "up")
        downs = sum(1 for r in rows if r.get("label") == "down")

        st.write(f"共收集到 {total} 条反馈，其中 👍 {ups} 条，👎 {downs} 条。")

        st.caption("最近 5 条反馈（问题 & 是否使用 RAG）：")
        for r in rows[-5:]:
            q = (r.get("question") or "")[:80]
            used_rag = r.get("used_rag")
            st.markdown(
                f"- **Q**: {q}..."
                f"  ｜ Used RAG: `{used_rag}` ｜ Label: `{r.get('label')}`"
            )
