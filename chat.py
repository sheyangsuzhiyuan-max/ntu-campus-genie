import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

# ✅ 改回标准写法 (环境修好后，这个才是对的)
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain


def run_chat(deepseek_api_key: str) -> None:
    """主聊天逻辑：根据是否有 vectorstore 决定走 RAG 还是普通对话。"""
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "你好！我是你的 AI 助手。请上传文档并点击构建知识库，然后问我相关问题。",
            }
        ]

    # 展示历史消息
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("请输入问题..."):
        if not deepseek_api_key:
            st.info("请先设置 API Key。")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        try:
            # DeepSeek 模型配置
            llm = ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
            )

            # RAG 模式判断
            if "vectorstore" in st.session_state:
                vectorstore = st.session_state["vectorstore"]
                retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

                # ... (前文代码不变) ...

                # --- 修改开始：优化 Prompt ---
                prompt_tmpl = ChatPromptTemplate.from_template(
                    """
                    你是一个热心、专业的 NTU 校园助手（学长/学姐风格）。
                    你的任务是帮助新同学解答关于签证、宿舍、选课等方面的问题。

                    请严格基于以下【背景信息】来回答用户的【问题】。

                    回答要求：
                    1. **语气亲切**：可以使用 emoji (如 🏠, 📅, 💡) 来缓解用户的焦虑。
                    2. **结构清晰**：如果答案包含步骤或多个选项，请务必使用 Markdown 列表（- 或 1.）列出。
                    3. **引用来源**：如果背景信息中提供了链接或来源，请在回答末尾附上。
                    4. **诚实守信**：如果【背景信息】里没有提到的内容，请直接说“抱歉，当前知识库中没有关于此问题的具体信息”，建议用户咨询学校 One Stop 中心。不要编造日期或价格。

                    【背景信息】：
                    {context}

                    【问题】：
                    {input}
                    """
                )
                # --- 修改结束 ---
                
                doc_chain = create_stuff_documents_chain(llm, prompt_tmpl)
                # ... (后文代码不变) ...

                doc_chain = create_stuff_documents_chain(llm, prompt_tmpl)
                rag_chain = create_retrieval_chain(retriever, doc_chain)

                with st.chat_message("assistant"):
                    st.caption("🔍 正在检索知识库...")
                    response = rag_chain.invoke({"input": prompt})
                    answer = response["answer"]

                    # Debug：展示参考文档片段
                    with st.expander("🕵️‍♂️ Debug: AI 参考了哪些文档片段？"):
                        retrieved_docs = retriever.invoke(prompt)
                        for i, doc in enumerate(retrieved_docs):
                            st.markdown(
                                f"**片段 {i+1} (来自 {doc.metadata.get('source', '未知')}):**"
                            )
                            st.text(doc.page_content)
                            st.divider()

                    st.write(answer)
            else:
                # 普通模式
                with st.chat_message("assistant"):
                    response = llm.invoke([HumanMessage(content=prompt)])
                    answer = response.content
                    st.write(answer)

            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )

        except Exception as e:
            st.error(f"发生错误: {e}")



