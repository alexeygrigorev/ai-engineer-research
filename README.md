# AI Engineering Interview Research

Research into AI engineering interview assignments, take-home challenges, and hiring practices from Q4 2025 / Q1 2026.

## Overview

This repository contains research on AI engineering interview processes, with a focus on:
- Actual take-home assignments given to candidates
- Personal interview experiences from engineers
- Common patterns and tech stacks
- Company-specific interview challenges

## Contents

### [`challenges/`](./challenges/)
- **`links.md`** - 65+ actual AI Engineer take-home assignments from GitHub
- **`methodology.md`** - Detailed research methodology
- **`blogs.md`** - 40+ blog posts and online resources
- **`interview-stories.md`** - 30+ personal interview stories from real engineers

### [`scrapers/`](./scrapers/)
Job scraping scripts for various platforms (Built In, Y Combinator, etc.)

### [`jobs/`](./jobs/)
- **`all_jobs.csv`** - 1,416 AI Engineer jobs from Built In (combined)
- **`builtin/`** - City-specific scraped data
- **`raw/`** - Raw HTML files
- **`extracted/`** - Jobs extracted to YAML

### [`research/`](./research/)
Compiled research notes and findings

## Key Findings

### Most Common Assignment Types (2025-2026)
1. **RAG Systems** (60%+) - Document Q&A, vector databases, LangChain/LangGraph
2. **Agentic Systems** (30%+) - ReACT agents, tool-calling, LangGraph workflows
3. **Conversational AI** (25%+) - Chatbots, Telegram/Discord bots

### Top Tech Stack
| Tool | Frequency |
|------|-----------|
| LangChain/LangGraph | 60%+ |
| OpenAI API | 50%+ |
| FastAPI | 40%+ |
| MongoDB Atlas | 30%+ |
| Streamlit | 25%+ |

---

## Job Scraper Setup

### Multi-threaded Built In Job Scraper (with Oxylabs proxy)

#### Setup on GitHub Codespace

1. **Create Codespace**: https://github.com/alexeygrigorev/ai-engineer-research → Code → Codespaces → Create

2. **Add .env file** (via SSH):
```bash
gh codespace ssh
cat > .env << 'EOF'
OXYLABS_ENDPOINT='pr.oxylabs.io:7777'
OXYLABS_USER='your_user'
OXYLABS_PASSWORD='your_password'
EOF
```

3. **Install dependencies**:
```bash
uv sync
```

#### Run Scraper

```bash
# Download all 1,416 job HTMLs (8 threads, 3 retries)
uv run python scrapers/download_all_html.py

# Extract to YAML
uv run python scrapers/extract_from_html.py --all
```

Output: `jobs/extracted/*.yaml` with fields: title, company, location, skills, description, etc.

---

## Contributing

This is a research repository. Feel free to submit PRs with additional interview assignments or stories.

## License

MIT License

---

*Last updated: February 2026*
