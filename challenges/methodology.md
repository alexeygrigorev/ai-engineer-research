# Research Methodology - AI Engineering Interview Assignments

## Overview
This document describes the research methodology used to find AI Engineering interview home assignments from Q4 2025 and Q1 2026.

## Data Collection Process

### 1. GitHub CLI Search Strategy

Primary tool: `gh search repos` - GitHub's command-line interface for searching repositories.

**Search Query Patterns:**

#### Core AI Engineer Assignment Searches
- `gh search repos "ai engineer" "take home"` - Found 40+ actual take-home assignments
- `gh search repos "ai engineer" "assignment" OR "task"`
- `gh search repos "ai" "interview" "assignment"`
- `gh search repos "ai" "case study" "engineer"`

#### RAG-Specific Searches
- `gh search repos "rag" "interview" OR "assignment"`
- `gh search repos "retrieval" "augmented" "generation" "challenge"`

#### LLM/GenAI Searches
- `gh search repos "llm" "assignment" OR "task"`
- `gh search repos "genai" "assignment" OR "take-home"`
- `gh search repos "openai" "challenge" OR "test" OR "task"`
- `gh search repos "anthropic" OR "claude" "assignment" OR "test"`

#### Agentic Systems
- `gh search repos "agent" "ai" "hiring" OR "interview"`
- `gh search repos "agentic" "ai" "assessment"`

#### Company-Specific Searches
- `gh search repos "interview" "company name"` (e.g., paidy, multiply-ai, cloudpilot-ai)

#### Hiring Challenge Searches
- `gh search repos "hiring" "challenge" "ai" OR "ml" OR "data"`
- `gh search repos "recruiting" "challenge" "ai"`

**GitHub Search Parameters:**
- `--limit 100` - Maximum results per search
- `--json name,url,updatedAt,description` - Structured JSON output
- `--jq` - For filtering and formatting results

### 2. Filtering Criteria

To ensure quality, repos were filtered to include ONLY:
- **Actual home assignments** given to candidates
- **Q4 2025 (Oct-Dec 2025) and Q1 2026 (Jan-Mar 2026)** timeframe
- **AI Engineer specific** (LLMs, RAG, Agents, GenAI) - NOT classic ML/Data Science

**Excluded:**
- Interview prep tools (e.g., "rag-interview-coach" - this HELPS you prepare, not an assignment)
- Framework implementations (e.g., "ollama-langchain-agents")
- Coding challenge platforms (e.g., general LeetCode-style repos)
- Non-AI assignments (e.g., fraud detection, credit scoring - these are ML/DS tasks)

### 3. Key Findings

**Total Assignments Found: 65+**

#### Breakdown by Type:
1. **Company-Specific Assignments** (15 repos)
   - ai_engineer_interview_2025 (RAG document chatbot)
   - automotive_llm_analysis (LLM analysis case study)
   - Chatbot-TabularData-Document-Challenge (Mekari)
   - And 12 more...

2. **Generic AI Engineer Take-Home Assignments** (40+ repos)
   - Multiple "AI-Engineer-Take-Home*" repos from various companies
   - Bithealth assessments (multiple repos)
   - Agentic AI assessments
   - RAG-focused assignments

3. **Hiring Challenges** (9 repos)
   - Argmax hiring challenges
   - GenAI hiring challenges
   - Company-specific recruiting challenges

4. **AI Challenge Competition Winners** (4 repos)
   - Google Chrome Built-in AI Challenge winners
   - Amazon Nova AI Challenge winners

### 4. Common Assignment Patterns

#### Most Frequent Tasks:
1. **RAG Systems** (40%+ of assignments)
   - Document upload (PDF, DOCX, TXT, MD)
   - Vector databases (MongoDB Atlas, Qdrant, FAISS, Pinecone)
   - LangChain/LangGraph orchestration
   - Citation support

2. **Agentic Systems** (25%+)
   - ReACT agents
   - Tool-calling
   - Multi-step reasoning
   - LangGraph workflows

3. **Conversational AI** (20%+)
   - Chatbots
   - Telegram/Discord bots
   - Voice assistants

4. **Document Processing** (15%)
   - PDF parsing
   - Data extraction
   - Compliance checking

#### Tech Stack Frequency:
| Tool | Frequency |
|------|-----------|
| LangChain/LangGraph | 60%+ |
| OpenAI API | 50%+ |
| FastAPI | 40%+ |
| MongoDB Atlas | 30%+ |
| Streamlit | 25%+ |
| Google Gemini | 20%+ |
| Anthropic Claude | 15%+ |
| FAISS | 15%+ |

### 5. Quality Indicators

When evaluating repos, the following indicators suggest a **genuine interview assignment**:
- Description contains: "take-home", "interview", "assignment", "assessment", "challenge"
- Repo name includes company name or role (e.g., "bithealth-ai-engineer-take-home")
- Recent updates (2025-2026)
- Clear problem statement in README
- Submission/answer key repos exist (indicating it's a real assignment)

**Red Flags** (not actual assignments):
- Name suggests it's a tool/helper (e.g., "rag-interview-prep", "ai-interview-coach")
- Generic ML tasks (fraud detection, loan approval - these are DS/ML roles)
- Framework demos (e.g., "langchain-rag-demo")

### 6. Online Research (In Progress)

Next phase: Searching for personal blogs discussing AI interview challenges from Q4 2025 / Q1 2026.

**Search targets:**
- Medium articles
- dev.to posts
- Substack newsletters
- Personal blogs
- LinkedIn articles

**Keywords:**
- "AI engineer interview take-home"
- "RAG interview assignment"
- "GenAI coding challenge"
- "LLM engineer assessment"

---

## Results Summary

- **65+ genuine AI Engineer interview assignments** identified
- **Majority are RAG-based** (document Q&A systems)
- **Growing trend toward agentic AI** assignments
- **Common tech stack:** LangChain + OpenAI + FastAPI + Vector DB

## Sources

All data sourced from GitHub public repositories using official GitHub CLI.
Additional blog research in progress.

*Last updated: February 4, 2026*
