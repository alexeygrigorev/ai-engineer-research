#!/usr/bin/env python3
"""
Fetch detailed job content for all 250 jobs using Jina Reader API.

This script:
1. Parses the 250_jobs.md file to extract all job listings
2. For each unique job link, fetches content via Jina Reader API
3. Saves each job as a separate markdown file
4. Creates an index.md with all jobs and their status
"""

import re
import os
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import html

# Configuration
SOURCE_FILE = Path(r"C:\Users\alexe\git\ai-engineer-research\report\250_jobs.md")
OUTPUT_FOLDER = Path(r"C:\Users\alexe\git\ai-engineer-research\jobs")
JINA_API_KEY = "jina_7f1404f4a026418c9d63eecccf517bb7n5a8p8BmKwY_2IFvxbuufHdIkP43"
JINA_API_URL = "https://r.jina.ai/"
REQUEST_DELAY = 2.0  # Seconds between requests to avoid rate limiting
MAX_RETRIES = 3
RETRY_DELAY = 5.0  # Seconds to wait before retry

# Ensure output folder exists
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """
    Clean a string to make it a valid filename.

    Args:
        name: The string to sanitize
        max_length: Maximum length of the filename

    Returns:
        A sanitized filename string
    """
    # Remove or replace problematic characters
    name = html.unescape(name)  # Decode HTML entities like &amp;
    name = name.replace("&", "_and_")
    name = re.sub(r'[<>:"/\\|?*]', '', name)  # Remove invalid filename chars
    name = name.replace(' ', '_')
    name = re.sub(r'_+', '_', name)  # Replace multiple underscores with single
    name = name.strip('_')  # Remove leading/trailing underscores
    name = name[:max_length]  # Truncate to max length
    return name if name else "unnamed"


def fetch_with_jina(url: str, retries: int = MAX_RETRIES) -> tuple[str, int]:
    """
    Fetch content from a URL using Jina Reader API.

    Args:
        url: The URL to fetch
        retries: Number of retries on failure

    Returns:
        A tuple of (content, status_code)
        content is the markdown text from Jina Reader
        status_code is the HTTP status code (or 0 for network errors)
    """
    for attempt in range(retries):
        try:
            response = requests.get(
                JINA_API_URL + url,
                headers={
                    "Authorization": f"Bearer {JINA_API_KEY}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                timeout=30
            )
            return response.text, response.status_code
        except requests.exceptions.Timeout:
            print(f"  [Timeout] Attempt {attempt + 1}/{retries}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            print(f"  [Error: {e}] Attempt {attempt + 1}/{retries}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)

    return "", 0


def parse_jobs_from_markdown(content: str) -> List[Dict]:
    """
    Parse job listings from the markdown file.

    Args:
        content: The markdown file content

    Returns:
        A list of job dictionaries with keys: number, title, company, location, date, source, link
    """
    jobs = []
    lines = content.split('\n')

    current_job = None
    job_number = 0

    for line in lines:
        # Match job number headers: ### 1. Job Title
        match = re.match(r'###\s+(\d+)\.\s+(.+)', line)
        if match:
            if current_job:
                jobs.append(current_job)

            job_number = int(match.group(1))
            current_job = {
                'number': job_number,
                'title': match.group(2).strip(),
                'company': '',
                'location': '',
                'date': '',
                'source': '',
                'link': ''
            }
            continue

        # Match job properties: **Key:** Value
        if current_job:
            prop_match = re.match(r'\*\*([^:]+):\*\*\s*(.+)', line)
            if prop_match:
                key = prop_match.group(1).lower().strip()
                value = prop_match.group(2).strip()

                if key == 'company':
                    current_job['company'] = value
                elif key == 'location':
                    current_job['location'] = value
                elif key == 'date posted':
                    current_job['date'] = value
                elif key == 'source':
                    current_job['source'] = value
                elif key == 'link':
                    current_job['link'] = value

    # Add the last job
    if current_job:
        jobs.append(current_job)

    return jobs


def generate_job_filename(job: Dict) -> str:
    """
    Generate a filename for a job posting.

    Args:
        job: Job dictionary

    Returns:
        A filename like: 001_Dakota_AI_Agent_Product_Engineer.md
    """
    number_str = f"{job['number']:03d}"
    company = sanitize_filename(job['company'] or 'Unknown')
    title = sanitize_filename(job['title'] or 'Unknown_Role')

    return f"{number_str}_{company}_{title}.md"


def save_job_content(job: Dict, content: str, status: str) -> str:
    """
    Save job content to a markdown file.

    Args:
        job: Job dictionary
        content: The fetched content (or error message)
        status: Status of the fetch ('success', 'error', 'skipped')

    Returns:
        The path to the saved file
    """
    filename = generate_job_filename(job)
    filepath = OUTPUT_FOLDER / filename

    # Prepare the markdown content
    md_content = f"""# Job {job['number']}: {job['title']}

**Company:** {job['company']}
**Location:** {job['location']}
**Date Posted:** {job['date']}

**Source:** {job['source']}

**Original Link:** {job['link']}

---

**Fetch Status:** {status}
**Fetched:** {datetime.now().isoformat()}

---

## Job Content

{content}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return str(filepath)


def create_index(jobs: List[Dict], results: List[Dict]) -> None:
    """
    Create an index.md file listing all jobs and their status.

    Args:
        jobs: List of all job dictionaries
        results: List of result dictionaries with fetch status
    """
    index_path = OUTPUT_FOLDER / "index.md"

    # Count statuses
    total = len(results)
    success = sum(1 for r in results if r['status'] == 'success')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    errors = sum(1 for r in results if r['status'] == 'error')
    unique_urls = len(set(r['url'] for r in results if r['url']))

    md_content = f"""# AI Engineer Jobs Index

**Generated:** {datetime.now().isoformat()}
**Source:** {SOURCE_FILE.name}

## Summary

- **Total Jobs:** {total}
- **Unique URLs:** {unique_urls}
- **Successfully Fetched:** {success}
- **Skipped (Duplicates):** {skipped}
- **Errors:** {errors}

---

## All Jobs

| # | Company | Title | Location | Status | File |
|---|---------|-------|----------|--------|------|
"""

    for result in results:
        job = result['job']
        status_icon = {
            'success': '✅',
            'skipped': '⏭️',
            'error': '❌'
        }.get(result['status'], '❓')

        file_link = result['filename'] if result['filename'] else 'N/A'
        if result['filename']:
            file_link = f"[{result['filename']}]({result['filename']})"

        md_content += f"| {job['number']} | {job['company']} | {job['title']} | {job['location']} | {status_icon} {result['status']} | {file_link} |\n"

    # Add statistics by source
    md_content += "\n---\n\n## Jobs by Source\n\n"
    source_counts = {}
    for result in results:
        source = result['job']['source']
        if source not in source_counts:
            source_counts[source] = {'total': 0, 'success': 0, 'error': 0}
        source_counts[source]['total'] += 1
        if result['status'] == 'success':
            source_counts[source]['success'] += 1
        if result['status'] == 'error':
            source_counts[source]['error'] += 1

    for source, counts in sorted(source_counts.items(), key=lambda x: x[1]['total'], reverse=True):
        md_content += f"- **{source}**: {counts['total']} jobs ({counts['success']} fetched, {counts['error']} errors)\n"

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"\n[Info] Index created: {index_path}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("AI Engineer Jobs Content Fetcher")
    print("=" * 60)
    print(f"Source: {SOURCE_FILE}")
    print(f"Output: {OUTPUT_FOLDER}")
    print(f"API: Jina Reader (r.jina.ai)")
    print(f"Request delay: {REQUEST_DELAY}s")
    print("=" * 60)

    # Read the source file
    print(f"\n[Step 1] Reading job listings from {SOURCE_FILE.name}...")
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse jobs
    print(f"[Step 2] Parsing job listings...")
    jobs = parse_jobs_from_markdown(content)
    print(f"[Info] Found {len(jobs)} job listings")

    # Track unique URLs to skip duplicates
    seen_urls: Set[str] = set()
    results = []

    print(f"\n[Step 3] Fetching job content via Jina Reader API...")
    print(f"[Info] This will take time due to rate limiting...")
    print("=" * 60)

    for i, job in enumerate(jobs, 1):
        url = job['link']

        print(f"\n[{i}/{len(jobs)}] Job {job['number']}: {job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  URL: {url}")

        result = {
            'job': job,
            'url': url,
            'status': 'pending',
            'filename': None,
            'error': None
        }

        # Check if this URL was already processed
        if url in seen_urls:
            print(f"  [Skip] Duplicate URL (already processed)")
            result['status'] = 'skipped'
            results.append(result)
            continue

        seen_urls.add(url)

        # Skip empty URLs
        if not url or url == '':
            print(f"  [Skip] No URL provided")
            result['status'] = 'skipped'
            results.append(result)
            continue

        # Fetch content via Jina Reader
        print(f"  [Fetch] Downloading content...")
        fetched_content, status_code = fetch_with_jina(url)

        if status_code == 200:
            # Success
            print(f"  [Success] Fetched {len(fetched_content)} characters")
            result['status'] = 'success'
            result['filename'] = generate_job_filename(job)
            save_job_content(job, fetched_content, 'success')
        elif status_code == 429:
            # Rate limited
            print(f"  [Error] Rate limited (429). Waiting {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
            # Retry once
            fetched_content, status_code = fetch_with_jina(url)
            if status_code == 200:
                print(f"  [Success] Retry successful")
                result['status'] = 'success'
                result['filename'] = generate_job_filename(job)
                save_job_content(job, fetched_content, 'success')
            else:
                print(f"  [Error] Retry failed with status {status_code}")
                result['status'] = 'error'
                result['error'] = f'HTTP {status_code}'
                save_job_content(job, f"Error: HTTP {status_code}\n\nCould not fetch content.", 'error')
        else:
            # Error
            print(f"  [Error] HTTP {status_code}")
            result['status'] = 'error'
            result['error'] = f'HTTP {status_code}'
            save_job_content(job, f"Error: HTTP {status_code}\n\nCould not fetch content.", 'error')

        results.append(result)

        # Rate limiting delay between requests
        if i < len(jobs):
            print(f"  [Wait] {REQUEST_DELAY}s delay before next request...")
            time.sleep(REQUEST_DELAY)

    # Create index
    print(f"\n[Step 4] Creating index...")
    create_index(jobs, results)

    # Final summary
    print("\n" + "=" * 60)
    print("FETCH COMPLETE")
    print("=" * 60)
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    print(f"Total jobs: {len(jobs)}")
    print(f"Successfully fetched: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Skipped (duplicates): {skipped_count}")
    print(f"\nOutput folder: {OUTPUT_FOLDER}")
    print(f"Index file: {OUTPUT_FOLDER / 'index.md'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
