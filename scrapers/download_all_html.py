#!/usr/bin/env python3
"""
Simple HTTP-based job scraper for Built In - no Playwright needed.
Uses requests library instead of browser automation.
Downloads with 8 threads for parallel processing.
"""
import os
import time
import csv
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

# Thread-safe set for tracking existing job IDs
existing_files = {f.stem.split('_')[-1] for f in RAW_DIR.glob("*.html")}
existing_lock = threading.Lock()


def get_proxy():
    """Get proxy configuration for this request."""
    return {
        "http": f"http://customer-{OXYLABS_USER}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}",
        "https": f"http://customer-{OXYLABS_USER}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}",
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


# Thread-safe counter and lock
counter_lock = threading.Lock()
success_count = 0
skipped_count = 0
failed_count = 0


def get_job_id(url):
    """Extract job ID from URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.path.split('/')[-1] if parsed.path.split('/')[-1] else 'unknown'


def process_url(idx, url, total):
    """Process a single URL - fetch and save HTML."""
    global success_count, skipped_count, failed_count

    job_id = get_job_id(url)

    # Check if already downloaded
    with existing_lock:
        if job_id in existing_files:
            global skipped_count
            skipped_count += 1
            print(f"  [{idx}/{total}] SKIP: {job_id}")
            return "skip"

    html, error = fetch_html(url)

    with counter_lock:
        if html:
            filename = save_html(url, html)
            with existing_lock:
                existing_files.add(job_id)
            success_count += 1
            print(f"  [{idx}/{total}] {filename}")
            return True
        else:
            failed_count += 1
            print(f"  [{idx}/{total}] Failed: {error[:50] if error else 'Unknown'}")
            return False, f"{url}|{error}"


def save_html(url, html):
    """Save HTML to file."""
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')

    # Get job ID from URL
    job_id = get_job_id(url)

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

    # No timestamp - just {title}_{job_id}.html
    filename = f"{title}_{job_id}.html"

    output_file = RAW_DIR / filename
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return filename


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Download job HTMLs with 8 threads')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to download (for testing)')
    args = parser.parse_args()

    global success_count, skipped_count, failed_count

    print("="*60)
    print("Simple HTTP Job Scraper (no Playwright)")
    print("8-Threaded Download")
    print("="*60)

    # Read URLs from deduplicated CSV
    csv_file = PROJECT_ROOT / "jobs" / "all_jobs_dedup.csv"
    if not csv_file.exists():
        print(f"ERROR: {csv_file} not found!")
        return

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        urls = [row['link'] for row in reader if row.get('link')]

    if args.limit:
        urls = urls[:args.limit]
        print(f"\nTEST MODE: Limited to {args.limit} URLs")

    print(f"\nFound {len(urls)} URLs in deduplicated CSV")
    print(f"Already downloaded: {len(existing_files)}")
    print(f"Threads: 8")
    print(f"Retries per URL: 3")
    print(f"Output: {RAW_DIR}")
    print(f"\nStarting download...\n")

    failed_urls = []

    # Process with 8 threads
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(process_url, i, url, len(urls)): (i, url)
            for i, url in enumerate(urls, 1)
        }

        for future in as_completed(futures):
            result = future.result()
            if result is not True and result != "skip":  # Failed
                failed_urls.append(result[1] if isinstance(result, tuple) else result)

    # Save failed URLs
    if failed_urls:
        FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FAILED_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(failed_urls))
        print(f"\n{len(failed_urls)} URLs failed - saved to {FAILED_FILE}")

    print("\n" + "="*60)
    print(f"COMPLETE: {success_count} downloaded, {skipped_count} skipped, {failed_count} failed")
    print(f"Files saved to: {RAW_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
