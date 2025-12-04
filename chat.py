import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

# ✅ 0.3.x 版本的唯一正确写法
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

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