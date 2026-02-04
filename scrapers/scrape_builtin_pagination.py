#!/usr/bin/env python3
"""
Built In job scraper with pagination support.
Navigates through all pages and extracts all job links.
"""
import os
import time
import json
import asyncio
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

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

OUTPUT_DIR = Path("../jobs/builtin")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Import shared extraction functions
from builtin_extractor import extract_builtin_job, html_to_markdown


BUILTIN_SITES = {
    "la": {
        "name": "LA, USA",
        "url": "https://www.builtinla.com/jobs?search=AI+engineer&allLocations=true",
    },
    "berlin": {
        "name": "Berlin, Germany",
        "url": "https://builtin.com/jobs?search=AI+Engineer&city=Berlin&state=Berlin&country=DEU&allLocations=true",
    },
    "london": {
        "name": "London, UK",
        "url": "https://builtin.com/jobs?search=AI+Engineer&city=London&state=England&country=GBR&allLocations=true",
    },
    "amsterdam": {
        "name": "Amsterdam, Netherlands",
        "url": "https://builtin.com/jobs?search=AI+Engineer&city=Amsterdam&state=Noord-Holland&country=NLD&allLocations=true",
    },
    "newyork": {
        "name": "New York, USA",
        "url": "https://builtin.com/jobs?search=AI+Engineer&city=New+York&state=New+York&country=USA&allLocations=true",
    },
}


async def get_all_job_links(page: Page, base_url: str) -> list:
    """
    Navigate through all pages and extract all job links.

    Args:
        page: Playwright Page object
        base_url: Starting URL for the search

    Returns:
        List of unique job URLs
    """
    all_links = []
    seen_links = set()
    page_num = 1

    print(f"  Starting pagination from: {base_url}")

    while True:
        # Construct URL for current page
        if page_num == 1:
            url = base_url
        else:
            # Add page parameter - Built In uses ?page=2
            separator = '&' if '?' in base_url else '?'
            url = f"{base_url}{separator}page={page_num}"

        print(f"    Page {page_num}: {url}")

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            if response.status != 200:
                print(f"      Got status {response.status}, stopping pagination")
                break

            # Wait for job listings to load
            await asyncio.sleep(3)

            # Scroll to ensure all content loads
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Extract all job links from current page
            page_links = await page.eval_on_selector_all(
                'a[href*="/job/"]',
                "els => els.map(e => e.href).filter(h => h.includes('/job/'))"
            )

            if not page_links:
                print(f"      No jobs found on page {page_num}, stopping")
                break

            # Add new links
            new_links = [link for link in page_links if link not in seen_links]
            for link in new_links:
                seen_links.add(link)
                all_links.append(link)

            print(f"      Found {len(page_links)} jobs ({len(new_links)} new)")

            # Check if there's a next page button
            # Look for next page button or link
            next_button = await page.query_selector('a[rel="next"], .pagination-next, a:has-text("Next")')
            if not next_button:
                # Also check if there are fewer jobs than usual (last page indicator)
                if len(page_links) < 20:  # Assuming ~20-25 jobs per page
                    print(f"      Only {len(page_links)} jobs on page {page_num}, likely last page")
                    break
            else:
                # Check if next button is disabled
                is_disabled = await next_button.is_disabled()
                if is_disabled:
                    print(f"      Next button disabled, stopping pagination")
                    break

            page_num += 1

            # Be respectful - add delay between pages
            await asyncio.sleep(2)

        except Exception as e:
            print(f"      Error on page {page_num}: {e}")
            break

    print(f"  Total unique jobs found: {len(all_links)}")
    return all_links


async def scrape_job_details(page: Page, job_url: str, site_name: str) -> dict:
    """Extract job details from a single job page."""
    try:
        job = await extract_builtin_job(page)

        if job and job.get('title') and job.get('description'):
            job['site'] = site_name
            job['scraped_at'] = datetime.now().isoformat()
            return job

    except Exception as e:
        print(f"      Error: {e}")

    return None


async def scrape_site(site_id: str, site_config: dict, max_jobs: int = None):
    """Scrape all jobs from a Built In site with full pagination."""
    print(f"\n{'='*60}")
    print(f"Scraping: Built In {site_config['name']}")
    print(f"{'='*60}")

    all_jobs = []

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

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        # Phase 1: Get all job links (with pagination)
        job_links = await get_all_job_links(page, site_config['url'])

        if max_jobs:
            job_links = job_links[:max_jobs]
            print(f"  Limited to {max_jobs} jobs")

        # Phase 2: Visit each job page and extract details
        print(f"\n  Extracting details from {len(job_links)} jobs...")
        for i, link in enumerate(job_links, 1):
            print(f"  [{i}/{len(job_links)}] {link}")

            job = await scrape_job_details(page, link, site_config['name'])

            if job:
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
                print(f"    -> {job.get('company')}: {job.get('title')[:40]}...")

            # Rate limiting
            await asyncio.sleep(3)

        await browser.close()

    # Save combined JSON
    if all_jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = OUTPUT_DIR / f"{site_id}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved {len(all_jobs)} jobs to {json_file}")

        # Create index
        index_file = OUTPUT_DIR / f"{site_id}_index.md"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(f"# Built In {site_config['name']} Jobs\n\n")
            f.write(f"*Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
            f.write(f"*Total Jobs: {len(all_jobs)}*\n\n")
            f.write(f"*Source:* {site_config['url']}\n\n")
            f.write("---\n\n## Jobs\n\n")
            for i, job in enumerate(all_jobs, 1):
                safe_title = job.get('title', '').replace('[', '\\[').replace(']', '\\]')
                f.write(f"{i}. [{safe_title}]({job.get('url')}) - {job.get('company')}\n")
        print(f"  Index saved to {index_file}")

    return all_jobs


async def main():
    print("="*60)
    print("Built In Job Scraper with Pagination")
    print("Extracts all AI Engineer jobs from all locations")
    print("="*60)

    import sys
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(BUILTIN_SITES.keys())

    # Check for max jobs limit
    max_jobs = None
    if "--max" in sites:
        idx = sites.index("--max")
        max_jobs = int(sites[idx + 1])
        sites = sites[:idx]

    print(f"\nSites to scrape: {sites}")
    if max_jobs:
        print(f"Max jobs per site: {max_jobs}")

    all_jobs = []
    for site_id in sites:
        if site_id not in BUILTIN_SITES:
            print(f"Unknown site: {site_id}")
            print(f"Available: {', '.join(BUILTIN_SITES.keys())}")
            continue

        site_config = BUILTIN_SITES[site_id]
        jobs = await scrape_site(site_id, site_config, max_jobs=max_jobs)
        all_jobs.extend(jobs)

    print(f"\n{'='*60}")
    print(f"COMPLETE - {len(all_jobs)} total jobs scraped")
    print(f"Saved to: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
