"""
Configuration file - Application constants and settings
"""

# API Configuration
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Default API Key (for testing/demo purposes)
# Reads from Streamlit secrets (both local .streamlit/secrets.toml and cloud)
import os

def get_api_key():
    """Get API key from Streamlit secrets or environment variable"""
    try:
        import streamlit as st
        return st.secrets.get("DEEPSEEK_API_KEY", None)
    except Exception:
        # Fallback to environment variable if not in Streamlit context
        return os.getenv("DEEPSEEK_API_KEY")

DEFAULT_API_KEY = get_api_key()

# Embedding Configuration
# Use multilingual model to support both Chinese and English queries
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# RAG Configuration
DEFAULT_CHUNK_SIZE = 500  # Reduced: smaller chunks = more focused semantic matching
DEFAULT_CHUNK_OVERLAP = 100  # Reduced proportionally
DEFAULT_RETRIEVAL_K = 10  # Increased: retrieve more candidates to avoid missing answers
USE_RERANK = False  # Disabled: rerank model has poor Chinese support
RERANK_TOP_K = 10  # Increased to match retrieval_k

# File Configuration
FEEDBACK_LOG_FILE = "feedback_log.csv"
SUPPORTED_FILE_TYPES = ["pdf", "txt"]

# Default Example Questions (English)
EXAMPLE_QUESTIONS = [
    "What are the monthly prices for single and twin rooms in graduate housing?",
    "How do I apply for graduate housing? What are the detailed steps?",
    "How do I get from NTU to Orchard? How much for MRT and taxi?",
    "What documents do I need to apply for Student's Pass?",
]

# Default Knowledge Base File Paths
DEFAULT_KNOWLEDGE_FILES = [
    "data/ntu_housing_extended.txt",  # Housing application guide
    "data/ntu_visa.txt",              # Visa/STP application guide
    "data/ntu_campus_life.txt",       # Campus life guide
    "data/ntu_academic_guide.txt",    # Academic guide
]

# Default URLs (for quick start)
DEFAULT_URLS = [
    "https://www.ntu.edu.sg/about-us/ntu2025",
    "https://www.ntu.edu.sg/life-at-ntu/accommodation",
]

# UI Text
WELCOME_MESSAGE = """Hello! I'm NTU Campus Genie.

Upload documents or build the knowledge base to get started, then ask me questions or click the example questions below!

💡 Tip: If you haven't set up a knowledge base yet, click the "Load Default Knowledge Base" button in the sidebar to get started quickly!"""

# System Prompts (Bilingual: English instruction, Chinese & English output)
SYSTEM_PROMPT_CHAT = """
You are a helpful and professional NTU campus assistant.
Please answer the user's [Question] based on the [Context Information] below.
If the information is not mentioned in the documents, please say "Not mentioned in the documents".

Please respond in both English and Chinese (中英双语回答):
- Provide the answer in English first
- Then provide the same answer in Chinese (中文)

[Context Information]:
{context}

[Question]:
{input}
"""

SYSTEM_PROMPT_HOUSING = """
You are an expert assistant familiar with NTU graduate housing.
Below are a student's housing preferences. Please provide recommendations based on the [Context Information].

Required output structure (respond in both English and Chinese):
1. Summarize their needs in 2-3 sentences
2. Recommend 1-2 specific housing options (e.g., Graduate Hall 1 twin sharing / North Hill single room),
   explaining why they are suitable (considering price, room type, private bathroom, etc.)
3. Provide a clear application checklist with bullet points, including:
   - When to submit the application in the system
   - Fees to pay (if mentioned in documents)
   - Important dates to check for housing results
If certain details are not mentioned in the documents, please clearly state "Not mentioned in the documents".

Please respond in both English and Chinese (中英双语回答).

[Student's Preferences]:
{preferences}

[Context Information]:
{context}

[Question]:
Based on the above preferences, please provide a detailed housing recommendation plan.
"""
