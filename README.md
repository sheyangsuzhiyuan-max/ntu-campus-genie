# ntu-campus-genie

> 🏫 **NTU Campus Genie** – a conversational assistant for NTU incoming graduate students, focusing on **graduate housing applications** and **Student’s Pass (STP) / student visa** workflows.  
> Built as a small RAG (Retrieval-Augmented Generation) demo on top of DeepSeek’s OpenAI-compatible API.

Online demo (Streamlit):  
https://ntu-campus-genie-7vjwvxeappj9vfjyilnogrk.streamlit.app/


## 1. Overview

### 1.1 Problem

For international graduate students coming to NTU, there are a few critical but confusing steps before arrival:

- Applying for **graduate housing** (hall types, prices, key dates, process)
- Applying for **Student’s Pass (STP)** (SOLAR flow, medical check-up, ICA visit, documents)

The information is:

- Scattered across multiple **official webpages, PDFs and emails**
- Mostly written in **formal English**
- Hard to search through and understand under time pressure

**NTU Campus Genie** is a conversational helper that lets students ask natural language questions (currently optimized for Chinese) and get structured answers grounded in official documents.

At the same time, this project serves as a small, end-to-end example of:

- Building a **Streamlit chatbot UI**
- Plugging in a **RAG pipeline** (documents + URLs → embeddings → vector store → retrieval)
- Using an **OpenAI-compatible LLM API (DeepSeek)**


### 1.2 Target users

- Incoming **international graduate students at NTU**
- Especially first-time newcomers to Singapore
- Primary language: Chinese (the current system prompt is in Chinese, but the model can also answer in English)


### 1.3 Current focus / scenarios

The current version ships with two sample text files (in Chinese):

1. **Graduate Hall Application Guide**  
   - Types of graduate halls (Graduate Hall 1/2, North Hill)  
   - Monthly rates  
   - Application key dates (for AY2025–2026)  
   - Application steps and FAQs

2. **Student’s Pass (STP) Application Guide**  
   - What STP is and who needs it  
   - SOLAR application flow (Form 16, Form V36, fees)  
   - Medical check-up requirements (HIV, X-ray, NTU clinic)  
   - Collecting the card at ICA and required documents

Users can upload these sample TXT files or their own NTU-related documents / URLs to build a small personal knowledge base.


## 2. Feature Highlights

- 💬 **Conversational UI**
  - Built with Streamlit’s native chat components
  - Maintains chat history in `st.session_state["messages"]`

- 📚 **RAG Knowledge Base (Documents + URLs)**
  - Upload local documents: `PDF` / `TXT`
  - Provide NTU-related URLs to scrape content
  - Use `RecursiveCharacterTextSplitter` to chunk text
  - Use `sentence-transformers/all-MiniLM-L6-v2` to generate embeddings
  - Store vectors in a local `FAISS` index

- 🧠 **DeepSeek Chat LLM (OpenAI-compatible)**
  - Uses `langchain_openai.ChatOpenAI` with:
    - `model="deepseek-chat"`
    - `base_url="https://api.deepseek.com/v1"`
  - API key is provided by the user in the sidebar
  - If a vector store exists → run RAG  
    If not → fall back to plain LLM chat

- 🧩 **Task-oriented system prompt**
  - The prompt frames the model as a *helpful NTU campus assistant*
  - Explicitly asks it to:
    - Answer based on **background context** from the documents
    - Say “文档中未提及” (“not mentioned in the documents”) when the answer is not in the knowledge base

- 📊 **Knowledge base stats**
  - After building the knowledge base, the app displays:
    - List of data sources (file names / URLs)
    - Character counts for each source


## 3. Architecture

### 3.1 High-level components

- **UI / Frontend** – `app.py`
  - Streamlit layout (sidebar + main page)
  - Sidebar:
    - DeepSeek API key input
    - Knowledge base builder (file upload + URL input)
  - Main page:
    - Title and basic description
    - Knowledge base stats
    - Chat widget

- **RAG pipeline** – `rag_pipeline.py`
  - Loads documents from:
    - Uploaded files (`PDF`, `TXT`)
    - Web pages via `WebBaseLoader`
  - Cleans and concatenates content
  - Splits documents with `RecursiveCharacterTextSplitter`
  - Embeds chunks with `HuggingFaceEmbeddings`
  - Stores vectors in `FAISS`
  - Tracks document stats (`name`, `chars`)
  - Saves `vectorstore` and `doc_stats` into `st.session_state`

- **Chat logic** – `chat.py`
  - Manages chat history with `st.session_state["messages"]`
  - Creates the DeepSeek LLM client via `ChatOpenAI`
  - If `vectorstore` exists:
    - Builds a retriever: `vectorstore.as_retriever(search_kwargs={"k": 6})`
    - Defines a `ChatPromptTemplate` with context + user input
    - Creates:
      - a document chain (`create_stuff_documents_chain`)
      - a retrieval chain (`create_retrieval_chain` or a local shim for compatibility)
    - Invokes the RAG chain and returns `response["answer"]`
  - If no `vectorstore`, calls the LLM directly with `HumanMessage`

### 3.2 Data flow (RAG mode)

1. User uploads files and/or enters URLs
2. `build_knowledge_base`:
   - Loads text from files and web
   - Splits into chunks
   - Creates embeddings using `all-MiniLM-L6-v2`
   - Saves vectors into a FAISS index
   - Stores the index in `st.session_state["vectorstore"]`
3. User asks a question in the chat
4. App checks for `vectorstore`:
   - If present:
     - Retrieves top-k relevant chunks
     - Injects them as `{context}` into the prompt
     - Calls the LLM to generate an answer grounded in those chunks
   - If absent:
     - Calls the LLM with the user message only


## 4. Requirements & Installation

### 4.1 Dependencies

From `requirements.txt`:

- `streamlit`
- `openai`
- `langchain==0.3.7`
- `langchain-community==0.3.7`
- `langchain-openai==0.2.3`
- `langchain-text-splitters==0.3.1`
- `sentence-transformers`
- `faiss-cpu`
- `pypdf`
- `tiktoken`
- `beautifulsoup4`


### 4.2 Setup

```bash
# 1) (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

