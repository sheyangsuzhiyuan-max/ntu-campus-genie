"""
Housing plan generation functionality
"""
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

from config import (
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_URL,
    DEFAULT_RETRIEVAL_K,
)
from rag_chain import create_retrieval_chain


def generate_housing_plan(preferences: dict, deepseek_api_key: str) -> str:
    """
    Generate housing recommendations based on user preferences and knowledge base.

    Args:
        preferences: dict with keys like 'budget', 'privacy', 'stay_term'
        deepseek_api_key: API key for DeepSeek

    Returns:
        Generated housing recommendation text
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

    # 使用带偏好信息的 prompt 模板
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
