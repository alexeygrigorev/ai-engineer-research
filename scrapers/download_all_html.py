#!/usr/bin/env python3
"""
Multi-threaded job scraper - downloads raw HTML from Built In job URLs.
Downloads all jobs from all_jobs.csv in parallel with retries.
"""
import os
import time
import asyncio
import csv
import random
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.async_api import async_playwright

from dotenv import load_dotenv

load_dotenv()

OXYLABS_ENDPOINT = os.getenv("OXYLABS_ENDPOINT", "pr.oxylabs.io:7777")
OXYLABS_USER = os.getenv("OXYLABS_USER")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
QUEUE_DIR = PROJECT_ROOT / "jobs" / "queue"
RAW_DIR = PROJECT_ROOT / "jobs" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FAILED_FILE = QUEUE_DIR / "failed_urls.txt"


def get_proxy_config():
    """Generate proxy config with unique session ID."""
    return {
        "server": f"http://{OXYLABS_ENDPOINT}",
        "username": f"customer-{OXYLABS_USER}-sessid-{int(time.time())}-{random.randint(1000,9999)}-sesstime-30",
        "password": OXYLABS_PASSWORD,
    }


async def fetch_html(url, retries=3):
    """Fetch HTML from a single URL with retries."""
    for attempt in range(retries):
        try:
            proxy = get_proxy_config()

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    proxy=proxy,
                    args=['--disable-blink-features=AutomationControlled']
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1920, "height": 1080}
                )

                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                html = await page.content()
                await browser.close()

                return html, None

        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
                continue
            return None, str(e)


def save_html(url, html):
    """Save HTML to file."""
    # Generate filename from URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    # Extract job ID from path
    path_parts = parsed.path.split('/')
    job_id = path_parts[-1] if path_parts[-1] else 'unknown'

    # Try to get title from HTML for better filename
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    title_tag = soup.find('h1')
    if title_tag:
        title = title_tag.get_text().strip()[:30]
        title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        title = title.strip('_')
    else:
        title = f"job_{job_id}"

    # Sanitize
    title = title.replace(' ', '_')
    title = ''.join(c if c.isalnum() or c in ('_', '-') else '' for c in title)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{title}_{job_id}_{timestamp}.html"

    output_file = RAW_DIR / filename
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return filename


def process_url(url):
    """Process a single URL - fetch and save HTML."""
    try:
        html, error = asyncio.run(fetch_html(url, retries=3))

        if html:
            filename = save_html(url, html)
            return {'url': url, 'status': 'success', 'file': filename}
        else:
            return {'url': url, 'status': 'failed', 'error': error}
    except Exception as e:
        return {'url': url, 'status': 'failed', 'error': str(e)}


def main():
    print("="*60)
    print("Multi-threaded Built In Job HTML Downloader")
    print("="*60)

    # Read URLs from CSV
    csv_file = PROJECT_ROOT / "jobs" / "all_jobs.csv"
    if not csv_file.exists():
        print(f"ERROR: {csv_file} not found!")
        print("Run combine_csv.py first to generate the CSV.")
        return

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        urls = [row['link'] for row in reader if row.get('link')]

    print(f"\nFound {len(urls)} URLs to download")
    print(f"Threads: 8")
    print(f"Retries per URL: 3")
    print(f"Output: {RAW_DIR}")
    print(f"\nStarting download...\n")

    success_count = 0
    failed_count = 0
    failed_urls = []

    # Process with 8 threads
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_url, url): url for url in urls}

        for future in as_completed(futures):
            url = futures[future]
            try:
                result = future.result(timeout=120)  # 2 min timeout per URL

                if result['status'] == 'success':
                    success_count += 1
                    print(f"  [{success_count}/{len(urls)}] ✓ {result['file']}")
                else:
                    failed_count += 1
                    failed_urls.append(result)
                    print(f"  [{success_count+failed_count}/{len(urls)}] ✗ {result.get('error', 'Unknown error')[:50]}")

            except Exception as e:
                failed_count += 1
                failed_urls.append({'url': url, 'error': str(e)})
                print(f"  [{success_count+failed_count}/{len(urls)}] ✗ Exception: {str(e)[:50]}")

    # Save failed URLs
    if failed_urls:
        with open(FAILED_FILE, 'w', encoding='utf-8') as f:
            for item in failed_urls:
                f.write(f"{item['url']}|{item.get('error', 'unknown')}\n")
        print(f"\n{len(failed_urls)} URLs failed - saved to {FAILED_FILE}")

    print("\n" + "="*60)
    print(f"COMPLETE: {success_count} downloaded, {failed_count} failed")
    print(f"Files saved to: {RAW_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
