#!/usr/bin/env python3
"""
Test scraper - extracts data from a single job posting page.
"""
import os
import time
import asyncio
import json
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

# Test job URLs - different platforms
TEST_URLS = {
    "builtin": "https://builtin.com/job/ai-engineer/8273513",
    "smartly": "https://builtin.com/job/staff-machine-learning-engineer-ai-product-lab/4438582",
    "sardine": "https://wellfound.com/role/r/machine-learning-engineer",
}


async def scrape_and_dump(url: str):
    """Scrape one page and dump everything we can find."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            proxy=PROXY_CONFIG,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        print(f"\n{'='*60}")
        print(f"Fetching: {url}")
        print(f"{'='*60}")

        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        print(f"Status: {response.status}")

        # Wait for page to fully load
        await asyncio.sleep(5)

        # Get page title
        title = await page.title()
        print(f"\nPage Title: {title}")

        # Get all text content
        all_text = await page.evaluate("() => document.body.innerText")
        print(f"\nPage text length: {len(all_text)} chars")
        print(f"\n--- First 1000 chars of page ---")
        print(all_text[:1000])

        # Try to find job description using various selectors
        print(f"\n--- Trying selectors ---")

        selectors_to_try = [
            ("h1", "Job title"),
            ("[class*='company']", "Company"),
            ("[class*='location']", "Location"),
            ("[class*='description']", "Description"),
            ("[class*='job-description']", "Job Description"),
            ("article", "Article content"),
            ("section", "Section content"),
            ("script[type='application/ld+json']", "JSON-LD structured data"),
        ]

        for selector, desc in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"\n  [{desc}] Found {len(elements)} elements with '{selector}'")
                    for i, el in enumerate(elements[:3]):  # First 3
                        text = await el.inner_text()
                        clean_text = text.strip()[:200]
                        print(f"    [{i+1}] {clean_text}...")
                        if "json" in selector:
                            content = await el.inner_text()
                            print(f"    JSON: {content[:200]}...")
            except Exception as e:
                print(f"  [{desc}] Error: {e}")

        # Get all links on page
        print(f"\n--- All links on page ---")
        links = await page.eval_on_selector_all("a[href]", "els => els.map(e => ({href: e.href, text: e.textContent?.trim().substring(0, 50)}))")
        for link in links[:10]:
            print(f"  {link}")

        # Get all class names that contain 'job' or 'description'
        print(f"\n--- Job-related class names ---")
        class_names = await page.evaluate("""
            () => {
                const all = document.querySelectorAll('*[class]');
                const classes = new Set();
                all.forEach(el => {
                    el.classList.forEach(c => {
                        if (c.toLowerCase().includes('job') ||
                            c.toLowerCase().includes('description') ||
                            c.toLowerCase().includes('company') ||
                            c.toLowerCase().includes('location')) {
                            classes.add(c);
                        }
                    });
                });
                return Array.from(classes);
            }
        """)
        for cn in class_names[:20]:
            print(f"  .{cn}")

        # Save full HTML for inspection
        html = await page.content()
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nSaved full HTML to: debug_page.html")

        print(f"\nPress Enter to close browser...")
        input()

        await browser.close()


if __name__ == "__main__":
    # Scrape Built In job first
    asyncio.run(scrape_and_dump(TEST_URLS["builtin"]))
