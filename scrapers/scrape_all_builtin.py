#!/usr/bin/env python3
"""
Built In full job scraper - fetches complete job descriptions.
Scrapes multiple Built In locations and visits each job page.
"""
import os
import time
import json
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page

# Import shared extraction functions
from builtin_extractor import extract_builtin_job, html_to_markdown

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

OUTPUT_DIR = Path("../jobs/builtin")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


BUILTIN_SITES = {
    "berlin": {
        "name": "Berlin - AI/ML",
        "url": "https://builtin.com/jobs/eu/germany/berlin/dev-engineering/search/artificial-intelligence",
        "pages": 5,
    },
    "london": {
        "name": "London - AI Engineer",
        "url": "https://builtinlondon.uk/jobs/dev-engineering/search/ai-engineer",
        "pages": 5,
    },
    "amsterdam": {
        "name": "Amsterdam - AI",
        "url": "https://builtin.com/jobs/eu/netherlands/amsterdam/dev-engineering/search/artificial-intelligence",
        "pages": 3,
    },
    "munich": {
        "name": "Munich - AI",
        "url": "https://builtin.com/jobs/eu/germany/dev-engineering/search/artificial-intelligence",
        "pages": 3,
    },
    "la": {
        "name": "LA - AI",
        "url": "https://www.builtinla.com/jobs/artificial-intelligence",
        "pages": 3,
    },
}


async def get_job_links(page: Page, url: str, max_pages: int) -> list:
    """Get all job links from a Built In search page."""
    links = []

    print(f"  Fetching job links from {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)

    # Scroll to load more
    for _ in range(3):
        await page.evaluate("window.scrollBy(0, 500)")
        await asyncio.sleep(0.5)

    # Get job links
    page_links = await page.eval_on_selector_all(
        "a[href*='/job/']",
        "els => els.map(e => e.href).filter(h => h.includes('/job/'))"
    )
    links.extend(page_links)

    print(f"    Page 1: {len(page_links)} jobs")

    # Try pagination
    for page_num in range(2, max_pages + 1):
        try:
            next_url = f"{url}?page={page_num}"
            await page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            page_links = await page.eval_on_selector_all(
                "a[href*='/job/']",
                "els => els.map(e => e.href).filter(h => h.includes('/job/'))"
            )

            if page_links:
                links.extend(page_links)
                print(f"    Page {page_num}: {len(page_links)} jobs")
            else:
                break

        except Exception as e:
            print(f"    Page {page_num}: Error - {e}")
            break

    # Deduplicate
    unique_links = list(set(links))
    print(f"  Total unique jobs: {len(unique_links)}")
    return unique_links


async def extract_job_details(page: Page, job_url: str) -> dict:
    """Extract full job details from a Built In job URL."""
    try:
        response = await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        if response.status != 200:
            return None

        await asyncio.sleep(2)

        # Use shared extraction function from builtin_extractor module
        return await extract_builtin_job(page)

    except Exception as e:
        print(f"      Error extracting: {e}")
        return None



async def scrape_site(site_id: str, site_config: dict, limit: int = None):
    """Scrape all jobs from a Built In site."""
    print(f"\n{'='*60}")
    print(f"Scraping: Built In {site_config['name']}")
    print(f"{'='*60}")

    all_jobs = []
    seen_urls = set()

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

        # Get job links
        job_links = await get_job_links(page, site_config['url'], site_config['pages'])

        if limit:
            job_links = job_links[:limit]

        # Visit each job page
        for i, link in enumerate(job_links, 1):
            if link in seen_urls:
                continue
            seen_urls.add(link)

            print(f"  [{i}/{len(job_links)}] {link}")

            job = await extract_job_details(page, link)

            if job and job.get('title') and job.get('description'):
                job['site'] = site_id
                job['scraped_at'] = datetime.now().isoformat()
                all_jobs.append(job)

                # Save individual job file
                safe_company = re.sub(r'[^\w\s-]', '', job.get('company', 'Unknown'))[:30]
                safe_title = re.sub(r'[^\w\s-]', '', job.get('title', 'Job'))[:50]
                filename = re.sub(r'\s+', '_', f"{safe_company}_{safe_title}").strip('_')

                description_md = html_to_markdown(job.get('description', ''))

                content = f"""# {job.get('title')}

**Company:** {job.get('company')}
**Location:** {job.get('location')}
**Level:** {job.get('level')}
**Employment Type:** {job.get('employment_type')}
**Company Size:** {job.get('company_size')}
**Source:** Built In {site_config['name']}
**Scraped:** {job.get('scraped_at')}
**URL:** {job.get('url')}

## Skills

{', '.join(job.get('skills', []))}

## Description

{description_md}
"""

                job_file = OUTPUT_DIR / f"{filename}.md"
                job_file.write_text(content, encoding='utf-8')

                print(f"    -> Saved: {job.get('company')}: {job.get('title')[:40]}...")

            await asyncio.sleep(3)  # Be respectful

        await browser.close()

    # Save combined JSON
    if all_jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = OUTPUT_DIR / f"{site_id}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved {len(all_jobs)} jobs to {json_file}")

    return all_jobs


async def main():
    print("="*60)
    print("Built In Full Job Scraper")
    print("Fetching complete job descriptions from all sites")
    print("="*60)

    import sys
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(BUILTIN_SITES.keys())

    # Check for limit
    limit = None
    if "--limit" in sites:
        idx = sites.index("--limit")
        limit = int(sites[idx + 1])
        sites = sites[:idx]

    print(f"\nSites to scrape: {sites}")
    if limit:
        print(f"Limit per site: {limit}")

    all_jobs = []
    for site_id in sites:
        if site_id not in BUILTIN_SITES:
            print(f"Unknown site: {site_id}")
            continue

        site_config = BUILTIN_SITES[site_id]
        jobs = await scrape_site(site_id, site_config, limit=limit)
        all_jobs.extend(jobs)

    print(f"\n{'='*60}")
    print(f"COMPLETE - {len(all_jobs)} full job descriptions scraped")
    print(f"Saved to: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
