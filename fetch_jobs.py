#!/usr/bin/env python3
"""Fetch job details from Jina Reader API for all 250 jobs."""
import os
import re
import time
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("JINA_READER_API_KEY")
INPUT_FILE = Path("report/250_jobs.md")
OUTPUT_DIR = Path("jobs")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
}

# Parse the 250_jobs.md file to extract job links
jobs = []
current_job = None

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    content = f.read()

# Split by job entries
job_pattern = r'### (\d+)\.\s+(.+?)\n\n\*\*Company:\*\*\s+(.+?)\n\n\*\*Location:\*\*\s+(.+?)\n\n\*\*Date Posted:\*\*\s+(.+?)\n\n\*\*Source:\*\*\s+(.+?)\n\n\*\*Link:\*\*\s+(.+?)\n\n---'

matches = re.findall(job_pattern, content, re.MULTILINE)

print(f"Found {len(matches)} jobs in 250_jobs.md")

seen_urls = set()
fetched = 0
failed = 0
skipped = 0

for match in matches:
    number, title, company, location, date, source, link = match
    number = int(number)

    # Clean up fields
    title = title.strip()
    company = company.strip()
    link = link.strip()

    # Skip duplicate URLs
    if link in seen_urls:
        skipped += 1
        print(f"Skipping duplicate URL: {number}. {title}")
        continue
    seen_urls.add(link)

    # Create safe filename
    safe_company = re.sub(r'[^\w\s-]', '', company)[:20].strip()
    safe_title = re.sub(r'[^\w\s-]', '', title)[:30].strip()
    filename = f"{number:03d}_{safe_company}_{safe_title}.md"
    filename = re.sub(r'\s+', '_', filename)

    output_path = OUTPUT_DIR / filename

    # Skip if already exists
    if output_path.exists():
        print(f"Already exists: {number}. {title}")
        fetched += 1
        continue

    # Skip Indeed links - not parsable with Jina
    if 'indeed.com' in link.lower():
        skipped += 1
        print(f"Skipping Indeed link: {number}. {title}")
        # Create a stub file with basic info
        stub_content = f"""# {title}

**Company:** {company}
**Location:** {location}
**Date Posted:** {date}
**Source:** {source}
**Original Link:** {link}

---

*Note: Indeed links cannot be fetched via Jina Reader. Visit the original link to view the full job posting.*

"""
        output_path.write_text(stub_content, encoding="utf-8")
        continue

    # Fetch from Jina Reader
    print(f"Fetching {number}/250: {title} at {company}...")

    try:
        response = requests.get(
            f"https://r.jina.ai/{link}",
            headers=HEADERS,
            timeout=30
        )

        if response.status_code == 200:
            markdown_content = response.text

            # Save with metadata header
            full_content = f"""# {title}

**Company:** {company}
**Location:** {location}
**Date Posted:** {date}
**Source:** {source}
**Original Link:** {link}

---

{markdown_content}
"""
            output_path.write_text(full_content, encoding="utf-8")
            fetched += 1
            print(f"  Saved: {filename}")
        else:
            failed += 1
            print(f"  Failed: HTTP {response.status_code}")

        # Rate limiting - Jina free tier has limits
        time.sleep(2)

    except Exception as e:
        failed += 1
        print(f"  Error: {e}")
        time.sleep(2)

# Create index
index_content = f"""# Job Fetch Index

**Total Jobs:** {len(matches)}
**Successfully Fetched:** {fetched}
**Failed:** {failed}
**Skipped (duplicates):** {skipped}

## All Jobs

| # | Title | Company | Location | File |
|---|-------|---------|----------|------|
"""

for match in matches:
    number, title, company, location, _, _, _ = match
    number = int(number)
    safe_company = re.sub(r'[^\w\s-]', '', company)[:20].strip()
    safe_title = re.sub(r'[^\w\s-]', '', title)[:30].strip()
    filename = f"{number:03d}_{safe_company}_{safe_title}.md"
    filename = re.sub(r'\s+', '_', filename)
    status = "✓" if (OUTPUT_DIR / filename).exists() else "✗"
    index_content += f"| {number} | {title} | {company} | {location} | [{status}]({filename}) |\n"

(OUTPUT_DIR / "index.md").write_text(index_content)

print(f"\nDone! Fetched: {fetched}, Failed: {failed}, Skipped: {skipped}")
