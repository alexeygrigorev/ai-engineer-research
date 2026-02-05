# Job Data Extraction Process

This document describes the process for extracting comprehensive skills and classifying AI roles (ai-first vs ai-support) from job descriptions.

## Goals

1. **Extract comprehensive skills** - The `skills` field from raw scraping is shallow (3-6 items). Need to extract all tools/technologies mentioned in the full description.

2. **Classify AI type** - Determine if a role is:
   - **ai-first**: Working directly on AI (building models, training, fine-tuning, prompt engineering, agent architecture)
   - **ai-support**: Working near AI but not building it (customer-facing, infrastructure, data pipelines, platform work)

## Data Structure

Input files: `jobs/extracted/*.yaml`

```yaml
job_id: 8064361
title: AI Engineer
company: LangChain
location:
work_type: FULL_TIME
level: Expert/Leader
skills:
  - AWS
  - Azure
  - GCP
  - Langchain
  - Langgraph
  - Python
  - Typescript
company_size: 123 Employees
description: |
  [Full markdown description with responsibilities, requirements, tech stack, etc.]
industries:
  - Information Technology
  - Software
  - Database
```

## Extraction Approach

### 1. Skills Extraction

Skills can be found in multiple places within a description:

| Source | Example | Notes |
|--------|---------|-------|
| **Existing `skills` field** | `["Langchain", "Python"]` | Use as base, don't duplicate |
| **"Technologies We Use" section** | Explicit tool lists | High confidence |
| **"What We're Looking For"** | Embedded in requirements | Look for tool names |
| **Responsibilities** | "Build agents with LangChain" | Context-dependent |
| **"About you" / Requirements** | "Proficiency with PyTorch" | Usually explicit |

#### Skill Categories to Extract

| Category | Examples |
|----------|----------|
| **LLM/GenAI Frameworks** | LangChain, LangGraph, LlamaIndex, DSPy, Haystack |
| **ML/DL Frameworks** | PyTorch, TensorFlow, JAX, scikit-learn, XGBoost |
| **Vector Stores** | Pinecone, Weaviate, Chroma, Qdrant, Faiss, pgvector |
| **Orchestration** | Airflow, Prefect, Dagster, Ray, Kubeflow |
| **Agent Tools** | MCP, function calling, CrewAI, AutoGen |
| **Prompt/Eval** | RAGAS, Truera, Arize, prompt engineering tools |
| **RAG/Search** | Vector search, semantic search, embeddings |
| **Fine-tuning** | LoRA, QLoRA, PEFT, RLHF, DPO |
| **Cloud** | AWS, Azure, GCP, specific services (S3, EC2, Bedrock) |
| **MLOps/LLMOps** | MLflow, Weights & Biases, Kubernetes, Docker |
| **API/Web** | FastAPI, REST, GraphQL, gRPC |
| **Data Engineering** | Spark, Databricks, Snowflake, dbt |
| **Frontend** | React, Vue, Next.js, TypeScript |
| **Backend Languages** | Python, Java, Go, Rust, C++ |
| **GPU/Compute** | CUDA, TensorRT, Triton, OpenMP |
| **Monitoring** | Prometheus, Grafana, Datadog |

#### Extraction Rules

1. **Normalize case** - "langchain" → "Langchain"
2. **Deduplicate** - "Python" and "python" → single entry
3. **Filter noise** - Skip common words (and, or, with, for, etc.)
4. **Handle variations** - "LLM Ops" and "LLMOps" → normalize
5. **Keep version-agnostic** - "PyTorch 2.0" → "PyTorch"

### 2. AI Type Classification

#### AI-First Indicators

| Pattern | Examples |
|---------|----------|
| **Verbs** | build, train, fine-tune, design, optimize, implement (with AI objects) |
| **Objects** | agents, models, LLMs, prompts, embeddings, RAG, vector stores |
| **Tech phrases** | "multi-agent systems", "prompt engineering", "LLMops", "fine-tuning" |
| **Explicit titles** | AI Engineer, ML Engineer, Applied Scientist, Research Engineer |
| **Core work** | Direct work on models, agents, prompts, evaluations |

**Note:** AI-first roles OFTEN ALSO work with cloud (AWS/GCP/Azure), data pipelines (Spark/Airflow), and infrastructure (Kubernetes/Docker). These are supporting skills for their AI work, not their primary focus.

#### AI-Support Indicators

| Pattern | Examples |
|---------|----------|
| **Customer-facing** | Account Engineer, Solutions Engineer, Customer Success, Sales Engineer |
| **Verbs** | support, guide, enable, advise, help (with customer) |
| **Only infrastructure** | "build infrastructure for AI" WITHOUT building AI themselves |
| **Platform roles** | Platform Engineer, Data Engineer (for ML teams) |
| **Using AI tools** | "leverage AI to help customers", "AI-powered tools" |

> **Important:** Cloud platforms (AWS, Azure, GCP), data pipelines, and infrastructure skills are common in **both** ai-first and ai-support roles. The distinction is:
> - **AI-first**: Builds AI models/agents AND uses cloud/data pipelines to deploy them
> - **AI-support**: ONLY works on cloud/data pipelines/platform, doesn't touch AI code/models

#### Classification Logic

**Key Principle:** Look for PRIMARY work focus. Cloud/data/infra skills are present in BOTH types.

```
if ai_first_score > ai_support_score and ai_first_score >= 2:
    return 'ai-first'
elif ai_support_score > ai_first_score and ai_support_score >= 2:
    return 'ai-support'
elif ai_first_score > 0:
    return 'ai-first'
elif ai_support_score > 0:
    return 'ai-support'
else:
    return 'unknown'
```

**Decision tree:**
1. Does the role BUILD AI models/agents/prompts? → ai-first
2. Does the role SUPPORT/ADE/ENABLE others working with AI? → ai-support
3. Does the role BUILD DATA PIPELINES FOR ML (but not ML itself)? → ai-support
4. If both AI work AND support work are mentioned → ai-first (they're hands-on)

## Output Format

Add to existing YAML:

```yaml
# ... existing fields ...

skills_comprehensive:
  - Langchain
  - Langgraph
  - Python
  - Typescript
  - AWS
  - Azure
  - GCP
  - RAG
  - Multi-agent systems
  - Prompt engineering
  - Vector stores
  - LLM evaluation
  - State management
  - CI/CD
  - REST APIs

skills_count: 15
ai_type: ai-first
ai_type_method: content_based
```

## Examples

### Example 1: LangChain AI Engineer (genai-first)

**Title:** AI Engineer
**Key description excerpts:**
> "Design multi-agent systems with Subagents/Handoffs/Router patterns"
> "implement agent logic using langchain/langgraph"
> "design comprehensive evaluation frameworks"
> "design RAG patterns with vector store integration"

**Classification:** `genai-first`
- Builds agents directly
- Uses LLM frameworks for implementation
- Designs RAG/evaluation systems
- Works on prompt optimization

**Skills extracted:**
- LLM Frameworks: Langchain, Langgraph, Langsmith
- Agent patterns: Subagents, Handoffs, Router, multi-agent systems
- RAG: Vector stores, RAG patterns, knowledge organization
- Evaluation: LLM-as-judge, deterministic evaluators
- State management, prompt engineering, MCP/tool integration

**Responsibilities:**
- Design multi-agent systems with Subagents/Handoffs/Router patterns
- Implement agent logic using langchain/langgraph
- Design comprehensive evaluation frameworks
- Optimize prompts with A/B testing
- Implement state management (short-term and long-term memory)
- Design RAG patterns with vector store integration
- Guide customers on agent deployment and configuration management
- Integrate agents into CI/CD pipelines
- Set up observability using LangSmith
- Lead agent engineering maturity assessments
- Work directly with enterprise customers

**Company:**
- Name: LangChain
- Size: 123 Employees
- Stage: Startup/Scale-up (Series B+ based on employee count)
- Industry: Information Technology, Software, Database
- Focus: LLM application framework and developer tools

### Example 2: Snowflake AI Account Engineer (ai-support)

**Title:** AI Account Engineer - Activation
**Key description excerpts:**
> "Accelerate the customer journey from initial acquisition"
> "Dedicated customer technical partner"
> "Leveraging modern AI-powered tools and coding agents to ensure technical success"
> "Strong foundational understanding of data architecture"

**Classification:** `ai-support`
- Customer-facing role
- Uses AI tools rather than building AI
- Focus on customer success/adoption
- Technical advisory, not model development

**Skills extracted:**
- Cloud: AWS, Azure, GCP
- Data: SQL, data architecture, data analytics
- Soft skills: communication, project management
- Tools: AI-powered development tools (general)

### Example 3: C the Signs AI Data Engineer (ai-support)

**Title:** AI Data Engineer
**Key description excerpts:**
> "Developing and fine-tuning data specifically for our LLMs"
> "Design, build, and maintain scalable data pipelines"
> "Collaborate with data scientists and machine learning engineers"
> "Work with the team to identify and acquire new data sources"

**Classification:** `ai-support`
- Builds infrastructure/pipelines FOR ML team
- Doesn't train or fine-tune models themselves
- Data lifecycle work, not model work
- Supports ML engineers' work

**Skills extracted:**
- Data: Apache Airflow, Spark, ETL, data modeling
- Cloud: AWS, Azure, GCP
- Languages: Python, Scala, Java
- Domain: Healthcare data standards (FHIR, HL7), HIPAA

## Edge Cases

| Situation | Treatment |
|-----------|-----------|
| **Forward Deployed Engineer (FDE)** | Usually ai-first - deploys AI solutions to customers, builds AI applications |
| **Data Scientist at AI company** | ai-first - builds models |
| **ML Engineer title but only platform work** | ai-support - infrastructure for ML, not ML itself |
| **AI in title but customer-facing** | ai-support - e.g., "AI Account Engineer" |
| **AI Product Engineer** | Check description - building AI features vs infra for AI team |
| **AI Data Engineer** | Usually ai-support - builds pipelines FOR ML team, not ML itself |
| **Has cloud/data skills AND AI skills** | ai-first - if they do AI work (cloud is supporting) |
| **Ambiguous descriptions** | Classify as `unknown` for manual review |

## Quality Checks

1. **Skills count reasonableness** - Should be 10-50 skills, not 3 or 100+
2. **AI type matches title roughly** - "ML Engineer" → likely ai-first
3. **No data leakage** - Don't classify based on company name alone
4. **Manual spot checks** - Review 5-10 random samples per batch
