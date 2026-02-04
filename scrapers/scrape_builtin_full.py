#!/usr/bin/env python3
"""
Built In job scraper - fetches FULL job descriptions.
Visits each job posting page to get complete details.
"""
import os
import time
import json
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page

if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

OXYLABS_ENDPOINT = os.getenv("OXYLABS_ENDPOINT", "pr.oxylabs.io:7777")
OXYLABS_USER = os.getenv("OXYLABS_USER")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")

PROXY_CONFIG = {
    "server": f"http://{OXYLABS_ENDPOINT}",
    "username": f"customer-{OXYLABS_USER}-sessid-{int(time.time())}-sesstime-10",
    "password": OXYLABS_PASSWORD,
}

OUTPUT_DIR = Path("jobs")
OUTPUT_DIR.mkdir(exist_ok=True)


BUILTIN_SITES = {
    "berlin": "https://builtin.com/jobs/eu/germany/berlin/dev-engineering/search/artificial-intelligence",
    "london": "https://builtinlondon.uk/jobs/dev-engineering/search/ai-engineer",
    "amsterdam": "https://builtin.com/jobs/eu/netherlands/amsterdam/dev-engineering/search/artificial-intelligence",
}


async def get_job_details(page: Page, job_url: str) -> dict:
    """Visit job page and extract full details."""
    try:
        response = await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        if response.status != 200:
            return None

        await asyncio.sleep(2)

        # Extract job details
        details = await page.evaluate("""
            () => {
                // Title
                const title = document.querySelector('h1, h2, .job-title, [class*="title"]')?.textContent?.trim() || '';

                // Company
                const company = document.querySelector('[class*="company"], .company-name')?.textContent?.trim() || '';

                // Location
                const location = document.querySelector('[class*="location"], .location')?.textContent?.trim() || '';

                // Description - get the main content
                const descSelectors = [
                    '[class*="description"]',
                    '[class*="job-description"]',
                    '.description',
                    'section[class*="details"]',
                    'article',
                ];

                let description = '';
                for (const sel of descSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.length > 100) {
                        description = el.textContent.trim();
                        break;
                    }
                }

                // Try to get structured data
                const script = document.querySelector('script[type="application/ld+json"]');
                if (script) {
                    try {
                        const data = JSON.parse(script.textContent);
                        if (data.description) description = data.description;
                    } catch (e) {}
                }

                return {
                    title,
                    company,
                    location,
                    description: description.substring(0, 10000), // Limit size
                    url: window.location.href
                };
            }
        """)

        return details

    except Exception as e:
        print(f"      Error fetching details: {e}")
        return None


async def scrape_builtin_jobs(site_name: str, base_url: str):
    """Scrape Built In jobs with full descriptions."""
    print(f"\n{'='*60}")
    print(f"Scraping: Built In {site_name.title()}")
    print(f"{'='*60}")

    jobs = []

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

        # First, get job links
        print(f"Fetching job listings from {base_url}")
        await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        # Scroll to load
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(0.5)

        # Get all job links
        job_links = await page.eval_on_selector_all(
            "a[href*='/job/']",
            "els => els.map(e => e.href).filter(h => h.includes('/job/'))"
        )

        # Deduplicate
        job_links = list(set(job_links))
        print(f"Found {len(job_links)} unique job links")

        # Now visit each job page
        for i, link in enumerate(job_links[:20], 1):  # Limit to 20 for testing
            print(f"  [{i}/{min(len(job_links), 20)}] Fetching: {link}")

            job_details = await get_job_details(page, link)
            if job_details and job_details.get('title'):
                job_details['source'] = 'builtin'
                job_details['scraped_at'] = datetime.now().isoformat()
                jobs.append(job_details)
                print(f"      -> {job_details.get('company', 'Unknown')}: {job_details.get('title', 'Unknown')[:40]}")

            await asyncio.sleep(3)  # Be respectful

        await browser.close()

    # Save results
    if jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        site_dir = OUTPUT_DIR / "builtin"
        site_dir.mkdir(exist_ok=True)

        # Save individual job files
        for i, job in enumerate(jobs, 1):
            safe_name = re.sub(r'[^\w\s-]', '', job.get('title', 'job'))[:50]
            safe_name = re.sub(r'\s+', '_', safe_name)
            filename = f"{i:03d}_{safe_name}.md"

            content = f"""# {job.get('title', 'Unknown')}

**Company:** {job.get('company', 'Unknown')}
**Location:** {job.get('location', 'Unknown')}
**Source:** Built In {site_name.title()}
**Scraped:** {job.get('scraped_at', '')}
**URL:** {job.get('url', '')}

---

## Description

{job.get('description', 'No description available.')}
"""
            (site_dir / filename).write_text(content, encoding='utf-8')

        # Also save combined JSON
        json_file = site_dir / f"{site_name}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

        print(f"\n  Saved {len(jobs)} jobs to {site_dir}/")

    return jobs


async def main():
    print("="*60)
    print("Built In Full Job Scraper")
    print("Fetching complete job descriptions")
    print("="*60)

    import re
    all_jobs = []

    for site_name, url in BUILTIN_SITES.items():
        jobs = await scrape_builtin_jobs(site_name, url)
        all_jobs.extend(jobs)

    print(f"\n{'='*60}")
    print(f"COMPLETE - {len(all_jobs)} full job descriptions scraped")
    print(f"Saved to: {OUTPUT_DIR}/builtin/")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
