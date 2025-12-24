### 1. Document Info

- **Product Name**: NTU Campus Genie
    
- **Owner**: [Your Name] – Associate AI PM (Candidate)
    
- **Version**: v0.2 (RAG + Housing Wizard)
    
- **Last Updated**: [fill date]
    

---

### 2. Background & Problem

NTU incoming international graduate students need to complete several critical tasks before and shortly after arrival, especially:

1. **Graduate housing application**
    
2. **Student’s Pass (STP) / student visa application**
    

Pain points:

- Information is **scattered** across multiple NTU webpages, PDFs and emails.
    
- Content is mostly in **formal English**, which is harder for many Chinese-speaking students.
    
- Students spend a lot of time **searching, cross-checking dates & requirements**, and still feel uncertain.
    
- There is **no unified, conversational entry point** to ask “stupid questions” safely.
    

---

### 3. Product Goal

Build a **conversational NTU onboarding assistant** that:

1. Answers common questions about **graduate housing** and **STP** based on **official documents**.
    
2. Provides a **guided “housing wizard” flow** to help students choose halls and understand application steps.
    
3. Collects basic feedback data (**👍 / 👎**) to inform future improvements.
    

---

### 4. Target Users & Personas

**Primary user**

- Incoming **international graduate students at NTU**, especially:
    
    - Chinese-speaking
        
    - First time living in Singapore
        
    - Limited time & energy to read long official docs
        

**Persona example**

- Name: Li Ming
    
- Age: 23
    
- Background: Chinese student admitted to NTU MSc, first time abroad
    
- Needs:
    
    - “Which hall should I apply for within my budget?”
        
    - “What exactly do I have to do for STP, and when?”
        
- Pain:
    
    - Not sure which info is up to date
        
    - Afraid of missing deadlines or critical steps
        

---

### 5. Scope (v0.2)

**In scope**

1. **RAG-based Q&A**
    
    - Upload NTU-related PDFs/TXT
        
    - Add NTU official URLs
        
    - Build a local vector store (FAISS)
        
    - Ask questions in Chinese or English and get answers grounded in docs
        
2. **Quick-start prompts**
    
    - Pre-defined buttons for:
        
        - “Graduate housing types & prices”
            
        - “Housing application deadlines”
            
        - “STP SOLAR process”
            
        - “STP medical check-up”
            
3. **Housing Wizard**
    
    - Collect user preferences:
        
        - Budget (low / medium / higher but comfortable)
            
        - Privacy / private bathroom importance
            
        - Planned stay length (1 semester / full year)
            
    - Generate:
        
        - Short summary of needs
            
        - 1–2 recommended housing options
            
        - A clear application checklist
            
4. **Feedback & Analytics (MVP)**
    
    - Per-answer 👍 / 👎
        
    - Log to `feedback_log.csv`
        
    - Simple analytics view:
        
        - Total feedback count
            
        - # of 👍 / 👎
            
        - Last 5 questions + whether RAG was used
            

**Out of scope (for now)**

- User login / authentication
    
- Multi-language UI beyond Chinese + English
    
- Complex dashboards or long-term storage in external DB
    
- Non-housing, non-STP flows (e.g. insurance, banking, course registration)
    

---

### 6. Key User Flows

#### Flow 1 – Build knowledge base & ask a question

1. User opens web app.
    
2. Enters **DeepSeek API key** in sidebar.
    
3. Uploads housing & STP documents OR pastes NTU URLs.
    
4. Clicks “Build knowledge base”.
    
5. System shows:
    
    - “Build completed”
        
    - List of sources (file / URL + char count)
        
6. User either:
    
    - Types a question in the chat, or
        
    - Clicks a **quick-start prompt** button.
        
7. Assistant:
    
    - Retrieves relevant chunks from vector store
        
    - Generates answer including key dates / fees / steps
        
    - Shows “Sources” section with the underlying documents/URLs
        
8. User leaves 👍 / 👎 feedback.
    

#### Flow 2 – Housing Wizard

1. User scrolls to **“Housing Application Wizard”** section.
    
2. Sets:
    
    - Budget preference
        
    - Privacy preference
        
    - Stay term
        
3. Clicks **“Generate housing recommendation & plan”**.
    
4. System:
    
    - Uses RAG over housing docs + preferences text
        
    - Returns:
        
        - Short summary of needs
            
        - Recommended halls (e.g. GH1 twin room / North Hill single room) + reason
            
        - Checklist: application window, fees, where to apply, what to watch out for
            
5. User can copy the checklist or ask follow-up questions in chat.
    

---

### 7. Functional Requirements

**FR-1: Knowledge base creation**

- FR-1.1: User can upload multiple PDF/TXT files.
    
- FR-1.2: User can paste multiple NTU URLs (one per line).
    
- FR-1.3: System chunks, embeds and indexes content in a local FAISS vector store.
    
- FR-1.4: System maintains a list of sources with:
    
    - `name`
        
    - `type` (file / URL)
        
    - character count
        

**FR-2: RAG Q&A**

- FR-2.1: When a knowledge base exists, Q&A must:
    
    - Retrieve top-k relevant chunks
        
    - Use them as context in the LLM prompt
        
- FR-2.2: When no knowledge base exists, fall back to plain LLM chat.
    
- FR-2.3: Answers should:
    
    - Be in Chinese by default (if user asks in Chinese)
        
    - Say **“文档中未提及”** when info is not present in docs.
        

**FR-3: Quick-start prompts**

- FR-3.1: Display 4 quick-start buttons grouped by scenario (Housing / STP).
    
- FR-3.2: Clicking a button fills a predefined question and triggers a chat turn.
    

**FR-4: Housing Wizard**

- FR-4.1: Provide UI controls (dropdowns) for:
    
    - Budget
        
    - Privacy
        
    - Stay term
        
- FR-4.2: On “Generate” click, call `generate_housing_plan`.
    
- FR-4.3: Output must follow structure:
    
    - Summary (2–3 sentences)
        
    - 1–2 recommendations with reasoning
        
    - Checklist (bullet list)
        

**FR-5: Feedback & Analytics**

- FR-5.1: Each assistant answer shows 👍 and 👎 buttons.
    
- FR-5.2: Clicking saves:
    
    - timestamp
        
    - label (`up` / `down`)
        
    - question
        
    - truncated answer
        
    - `used_rag`
        
    - `sources`
        
- FR-5.3: Analytics panel summarizes:
    
    - total feedback
        
    - up / down counts
        
    - last 5 feedback items
        

---

### 8. Non-functional Requirements

- **NFR-1: Performance**
    
    - Initial knowledge base build for ~5 short docs should finish within 10–20 seconds.
        
- **NFR-2: Reliability**
    
    - If RAG chain fails, app should show a friendly error message.
        
- **NFR-3: Privacy**
    
    - API key is only stored in Streamlit session state, not logged.
        
- **NFR-4: Usability**
    
    - New users should understand what to do in < 10 seconds (API key → knowledge base → ask).
        

---

### 9. Success Metrics (for a demo/portfolio)

Because this is a prototype, metrics are mostly **qualitative / demo-oriented**:

- At least **70% of common questions** in a prepared test set are answered correctly when docs are present.
    
- During user testing with classmates:
    
    - ≥ 4/5 rating on “easy to understand housing steps”
        
- In feedback_log:
    
    - More 👍 than 👎 on housing/STP answers.
        

---

### 10. Risks & Future Work

**Risks**

- Official rules & dates change frequently; docs may become outdated.
    
- RAG may still hallucinate if docs are incomplete.
    

**Next steps**

- Add explicit “Last updated” indicator for each source.
    
- Mark parts of answers as “official source” vs “advice”.
    
- Extend flows to other onboarding tasks (insurance, banking, SIM card, etc.).
    

---