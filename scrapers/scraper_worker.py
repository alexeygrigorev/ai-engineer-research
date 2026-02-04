#!/usr/bin/env python3
"""
Distributed scraper worker with todo/done queue.

Usage:
    python scraper_worker.py --init <url-file>     # Initialize todo list from URLs
    python scraper_worker.py --worker              # Run worker (processes one URL at a time)
    python scraper_worker.py --status              # Show status
"""
import os
import time
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

from dotenv import load_dotenv

load_dotenv()

OXYLABS_ENDPOINT = os.getenv("OXYLABS_ENDPOINT", "pr.oxylabs.io:7777")
OXYLABS_USER = os.getenv("OXYLABS_USER")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")

PROXY_CONFIG = {
    "server": f"http://{OXYLABS_ENDPOINT}",
    "username": f"customer-{OXYLABS_USER}-sessid-{int(time.time())}-sesstime-10",
    "password": OXYLABS_PASSWORD,
}

# Queue files
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
QUEUE_DIR = PROJECT_ROOT / "jobs" / "queue"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

TODO_FILE = QUEUE_DIR / "todo.txt"
DONE_FILE = QUEUE_DIR / "done.txt"
RAW_DIR = PROJECT_ROOT / "jobs" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def init_todo_list(urls):
    """Initialize todo list from URLs."""
    existing = set()
    if TODO_FILE.exists():
        existing.update(TODO_FILE.read_text().strip().split('\n'))
    if DONE_FILE.exists():
        existing.update(DONE_FILE.read_text().strip().split('\n'))

    new_urls = [u.strip() for u in urls if u.strip() and u.strip() not in existing]

    with open(TODO_FILE, 'a') as f:
        for url in new_urls:
            f.write(url + '\n')

    print(f"Added {len(new_urls)} URLs to todo list")
    print(f"Total todo: {len(TODO_FILE.read_text().strip().split('\n')) if TODO_FILE.exists() else 0}")


def get_next_url():
    """Get next URL from todo list (atomic operation)."""
    if not TODO_FILE.exists():
        return None

    with open(TODO_FILE, 'r') as f:
        lines = f.readlines()

    if not lines:
        return None

    # Get first URL
    url = lines[0].strip()

    # Write remaining lines back (atomically)
    remaining = lines[1:]
    with open(TODO_FILE, 'w') as f:
        f.writelines(remaining)

    return url


def mark_done(url):
    """Mark URL as done."""
    with open(DONE_FILE, 'a') as f:
        f.write(url + '\n')


async def scrape_url(url):
    """Scrape a single URL and save raw HTML."""
    print(f"Fetching: {url}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy=PROXY_CONFIG,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )

            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # Get HTML
            html = await page.content()

            await browser.close()

            # Save raw HTML
            # Generate filename from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            filename = parsed.path.replace('/', '_').replace('.html', '').strip('_')
            if not filename:
                filename = 'page'

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_DIR / f"{filename}_{timestamp}.html"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)

            print(f"  Saved: {output_file.name}")
            return True

    except Exception as e:
        print(f"  Error: {e}")
        return False


async def worker(limit=None):
    """Worker that processes URLs from todo list."""
    processed = 0

    while True:
        if limit and processed >= limit:
            print(f"\nReached limit of {limit} URLs")
            break

        url = get_next_url()

        if not url:
            print("\nNo more URLs in todo list")
            break

        success = await scrape_url(url)
        mark_done(url)
        processed += 1

        # Small delay between requests
        await asyncio.sleep(2)

    print(f"\nProcessed {processed} URLs")


def show_status():
    """Show queue status."""
    todo_count = 0
    done_count = 0

    if TODO_FILE.exists():
        todo_count = len(TODO_FILE.read_text().strip().split('\n')) if TODO_FILE.read_text().strip() else 0

    if DONE_FILE.exists():
        done_count = len(DONE_FILE.read_text().strip().split('\n')) if DONE_FILE.read_text().strip() else 0

    raw_count = len(list(RAW_DIR.glob("*.html")))

    print(f"Todo:     {todo_count}")
    print(f"Done:     {done_count}")
    print(f"Raw HTML: {raw_count}")


async def main():
    parser = argparse.ArgumentParser(description='Distributed scraper worker')
    parser.add_argument('--init', help='Initialize todo list from file')
    parser.add_argument('--worker', action='store_true', help='Run worker')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to process')

    args = parser.parse_args()

    if args.init:
        # Read URLs from file
        urls = Path(args.init).read_text().strip().split('\n')
        init_todo_list(urls)
    elif args.worker:
        await worker(limit=args.limit)
    elif args.status:
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
