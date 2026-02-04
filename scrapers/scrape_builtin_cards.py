#!/usr/bin/env python3
"""
Built In job card scraper - working version.
Extracts directly from job cards on listing pages.
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

# Get script directory and go up to project root for output
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "jobs" / "builtin"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


BUILTIN_SITES = {
    "la": {
        "name": "LA, USA (Global)",
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


async def extract_jobs_from_page(page: Page):
    """Extract jobs from current page."""
    jobs = []

    # Extract all job data
    card_data = await page.evaluate('''
        () => {
            const results = [];

            // Find all job title links
            const titleLinks = document.querySelectorAll('h2 a[href*="/job/"]');

            for (const titleLink of titleLinks) {
                const result = {};

                // Title and Link
                result.title = titleLink.textContent.trim();
                result.link = titleLink.href;

                // Find company link
                let companyLink = titleLink.closest('div')?.querySelector('a[href*="/company"]');
                if (!companyLink) {
                    const parent = titleLink.closest('div');
                    if (parent) {
                        const grandparent = parent.parentElement;
                        if (grandparent) {
                            companyLink = grandparent.querySelector('a[href*="/company"]');
                        }
                    }
                }

                if (companyLink) {
                    // Get company name from image alt attribute
                    const img = companyLink.querySelector('img[data-id="company-img"], img[alt*="Logo"]');
                    if (img && img.alt) {
                        result.company = img.alt.replace(' Logo', '').replace(' logo', '').trim();
                    } else {
                        // Fallback to span text
                        const span = companyLink.querySelector('span');
                        result.company = span ? span.textContent.trim() : companyLink.textContent.trim();
                    }
                } else {
                    result.company = '';
                }

                // Find parent card
                let card = titleLink.closest('div[id^="job-card-"]') ||
                           titleLink.closest('.job-bounded-responsive') ||
                           titleLink.closest('[class*="job"]') ||
                           titleLink.closest('div').parentElement;

                if (card) {
                    // Helper function to extract icon text
                    const getIconText = (iconClass) => {
                        const icon = card.querySelector('.' + iconClass);
                        if (icon) {
                            let parent = icon.parentElement;
                            while (parent && parent !== card) {
                                const text = parent.textContent.replace(/\\s+/g, ' ').trim();
                                if (text && text.length < 100 && text !== iconClass) {
                                    return text;
                                }
                                parent = parent.parentElement;
                            }
                        }
                        return '';
                    };

                    result.location = getIconText('fa-location-dot');
                    result.work_type = getIconText('fa-house-building');
                    result.compensation = getIconText('fa-sack-dollar');
                    result.level = getIconText('fa-trophy');
                }

                // Only add if we have title and company
                if (result.title && result.company) {
                    results.push(result);
                }
            }

            return results;
        }
    ''')

    return card_data


async def scrape_site(site_id: str, site_config: dict):
    """Scrape all jobs from a Built In site."""
    print(f"\n{'='*60}")
    print(f"Scraping: {site_config['name']}")
    print(f"URL: {site_config['url']}")
    print(f"{'='*60}")

    all_jobs = []
    seen_links = set()

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
        page_num = 1

        while True:
            # Build URL
            url = site_config['url']
            if page_num > 1:
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}page={page_num}"

            print(f"  Page {page_num}: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)

                # Wait for job cards to load
                await page.wait_for_selector('h2 a[href*="/job/"]', timeout=15000)

                # Scroll
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # Extract jobs
                page_jobs = await extract_jobs_from_page(page)

                # Filter duplicates
                new_jobs = [j for j in page_jobs if j['link'] not in seen_links]
                for job in new_jobs:
                    seen_links.add(job['link'])
                    all_jobs.append(job)

                if not page_jobs:
                    print(f"    No jobs on page {page_num}, stopping")
                    break

                print(f"    Got {len(page_jobs)} jobs ({len(new_jobs)} new)")

                # Show first few jobs
                for job in page_jobs[:3]:
                    print(f"      - {job['company']}: {job['title'][:50]}...")

                # Check if we should continue
                if len(page_jobs) < 15:
                    print(f"    Only {len(page_jobs)} jobs, likely last page")
                    break

                page_num += 1
                await asyncio.sleep(2)

            except Exception as e:
                print(f"    Error on page {page_num}: {e}")
                break

        await browser.close()

    # Save results
    if all_jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_file = OUTPUT_DIR / f"{site_id}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)

        # Save Markdown table
        md_file = OUTPUT_DIR / f"{site_id}_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# Built In {site_config['name']} - AI Engineer Jobs\n\n")
            f.write(f"*Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
            f.write(f"*Total Jobs: {len(all_jobs)}*\n\n")
            f.write(f"---\n\n")

            for i, job in enumerate(all_jobs, 1):
                f.write(f"## {i}. {job['title']}\n\n")
                f.write(f"**Company:** {job['company']}\n\n")
                f.write(f"**Location:** {job.get('location', 'N/A')}\n\n")
                f.write(f"**Type:** {job.get('work_type', 'N/A')}\n\n")
                f.write(f"**Level:** {job.get('level', 'N/A')}\n\n")
                f.write(f"**Compensation:** {job.get('compensation', 'N/A')}\n\n")
                f.write(f"**Link:** {job['link']}\n\n")
                f.write("---\n\n")

        print(f"\n  Saved {len(all_jobs)} jobs:")
        print(f"    JSON: {json_file}")
        print(f"    Markdown: {md_file}")

    return all_jobs


async def main():
    print("="*60)
    print("Built In Job Card Scraper")
    print("="*60)

    import sys
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(BUILTIN_SITES.keys())

    all_jobs = []
    for site_id in sites:
        if site_id not in BUILTIN_SITES:
            print(f"Unknown site: {site_id}")
            print(f"Available: {', '.join(BUILTIN_SITES.keys())}")
            continue

        site_config = BUILTIN_SITES[site_id]
        jobs = await scrape_site(site_id, site_config)
        all_jobs.extend(jobs)

    print(f"\n{'='*60}")
    print(f"COMPLETE - {len(all_jobs)} total jobs")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
