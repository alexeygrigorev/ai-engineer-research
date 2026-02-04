#!/usr/bin/env python3
"""
Simple HTTP-based job scraper for Built In - no Playwright needed.
Uses requests library instead of browser automation.
"""
import os
import time
import csv
import random
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from dotenv import load_dotenv

load_dotenv()

OXYLABS_ENDPOINT = os.getenv("OXYLABS_ENDPOINT", "pr.oxylabs.io:7777")
OXYLABS_USER = os.getenv("OXYLABS_USER")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR = PROJECT_ROOT / "jobs" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
FAILED_FILE = PROJECT_ROOT / "jobs" / "queue" / "failed_urls.txt"


def get_proxy():
    """Get proxy configuration for this request."""
    return {
        "http": f"http://{OXYLABS_USER}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}",
        "https": f"http://{OXYLABS_USER}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}",
    }


def fetch_html(url, timeout=60, retries=3):
    """Fetch HTML from a single URL with retries."""
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                proxies=get_proxy(),
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            response.raise_for_status()
            return response.text, None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return None, str(e)


def save_html(url, html):
    """Save HTML to file."""
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')

    # Get job ID from URL
    parsed = urlparse(url)
    job_id = parsed.path.split('/')[-1] if parsed.path.split('/')[-1] else 'unknown'

    # Get title for filename
    title_tag = soup.find('h1')
    if title_tag:
        title = title_tag.get_text().strip()[:30]
        title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        title = title.strip('_').strip('-')
    else:
        title = f"job_{job_id}"

    title = title.replace(' ', '_')
    title = ''.join(c if c.isalnum() or c in ('_', '-') else '' for c in title)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{title}_{job_id}_{timestamp}.html"

    output_file = RAW_DIR / filename
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return filename


def main():
    print("="*60)
    print("Simple HTTP Job Scraper (no Playwright)")
    print("="*60)

    # Read URLs from CSV
    csv_file = PROJECT_ROOT / "jobs" / "all_jobs.csv"
    if not csv_file.exists():
        print(f"ERROR: {csv_file} not found!")
        return

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        urls = [row['link'] for row in reader if row.get('link')]

    print(f"\nFound {len(urls)} URLs to download")
    print(f"Retries per URL: 3")
    print(f"Output: {RAW_DIR}")
    print(f"\nStarting download...\n")

    success_count = 0
    failed_count = 0
    failed_urls = []

    for i, url in enumerate(urls, 1):
        html, error = fetch_html(url)

        if html:
            filename = save_html(url, html)
            success_count += 1
            print(f"  [{i}/{len(urls)}] {filename}")
        else:
            failed_count += 1
            failed_urls.append(f"{url}|{error}")
            print(f"  [{i}/{len(urls)}] Failed: {error[:50] if error else 'Unknown'}")

        # Small delay between requests
        time.sleep(0.5)

    # Save failed URLs
    if failed_urls:
        with open(FAILED_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(failed_urls))
        print(f"\n{len(failed_urls)} URLs failed - saved to {FAILED_FILE}")

    print("\n" + "="*60)
    print(f"COMPLETE: {success_count} downloaded, {failed_count} failed")
    print(f"Files saved to: {RAW_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
