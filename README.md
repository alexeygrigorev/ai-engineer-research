# AI Engineering Interview Research

Research into AI engineering interview assignments, take-home challenges, and hiring practices from Q4 2025 / Q1 2026.


## Job Scraper Setup

### Built In Job Scraper (with Oxylabs proxy)

Built In is server-side rendered - no JavaScript/Playwright needed!

#### Setup on GitHub Codespace

1. **Create Codespace**: https://github.com/alexeygrigorev/ai-engineer-research → Code → Codespaces → Create

2. **Add .env file** (via SSH):
```bash
gh codespace ssh
cat > .env << 'EOF'
OXYLABS_ENDPOINT='pr.oxylabs.io:7777'
OXYLABS_USER='scrape_UWOhB'
OXYLABS_PASSWORD='9PFFaLPfvOtC='
EOF
```

3. **Install dependencies**:
```bash
uv sync
```

#### Run Scraper

```bash
# 1. Download all job HTMLs (1,416 jobs, retries=3)
uv run python scrapers/download_all_html.py

# 2. Extract all HTML files to YAML
uv run python scrapers/extract_from_html.py --all

# 3. Extract a single HTML file
uv run python scrapers/extract_from_html.py jobs/raw/file.html
```

**Output:** `jobs/extracted/*.yaml`

**YAML fields:**
```yaml
title: Senior AI/Data Engineer
company: WorkWave
location: USA
work_type: FULL_TIME
level: Expert/Leader
skills: [Python, AWS, Airflow, dbt]
company_size: 1,000 Employees
compensation: $160,000 - $180,000/year
description: |
  Full job description with line breaks preserved...
posted_date: 2026-01-18
url: https://builtin.com/job/...
source: Built In
```


*Last updated: February 2026*
