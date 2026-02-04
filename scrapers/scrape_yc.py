#!/usr/bin/env python3
"""
Y Combinator Work at a Startup job scraper.
"""
import os
import time
import json
import asyncio
import sys
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

OUTPUT_DIR = Path("jobs_raw")
OUTPUT_DIR.mkdir(exist_ok=True)


YC_SEARCHES = {
    "ai_engineer": {
        "name": "YC - AI Engineer",
        "url": "https://workatastartup.com/jobs?role=engineering&q=ai+engineer",
    },
    "ml_engineer": {
        "name": "YC - ML Engineer",
        "url": "https://workatastartup.com/jobs?role=engineering&q=machine+learning",
    },
    "ml_ops": {
        "name": "YC - MLOps",
        "url": "https://workatastartup.com/jobs?role=engineering&q=mlops",
    },
}


async def extract_yc_job(page: Page, job_card) -> dict:
    """Extract job from YC job card."""
    try:
        # Try different selectors
        title_elem = await job_card.query_selector("h3, h2, .job-title, [class*='title']")
        company_elem = await job_card.query_selector(".company-name, [class*='company'], a[class*='company']")
        location_elem = await job_card.query_selector(".location, [class*='location']")

        title = await title_elem.inner_text() if title_elem else ""
        company = await company_elem.inner_text() if company_elem else ""
        location = await location_elem.inner_text() if location_elem else "Remote"

        # Get link
        link_elem = await job_card.query_selector("a[href*='/jobs/']")
        link = await link_elem.get_attribute("href") if link_elem else ""
        if link and not link.startswith("http"):
            link = urljoin("https://workatastartup.com", link)

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "link": link,
            "source": "ycombinator",
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return None


async def scrape_yc():
    """Scrape Y Combinator jobs."""
    print("="*60)
    print("Y Combinator Job Scraper")
    print("="*60)

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

        for search_id, search_config in YC_SEARCHES.items():
            print(f"\nScraping: {search_config['name']}")
            print(f"URL: {search_config['url']}")

            try:
                await page.goto(search_config['url'], wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

                # YC uses infinite scroll - scroll to load more
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(1)

                # Find job cards - try various selectors
                job_cards = []
                selectors = [
                    "a[href*='/jobs/']",
                    "[class*='job']",
                    "article",
                ]

                for selector in selectors:
                    cards = await page.query_selector_all(selector)
                    if cards:
                        job_cards = cards
                        print(f"  Found {len(cards)} elements with: {selector}")
                        break

                seen = set()
                for card in job_cards:
                    job = await extract_yc_job(page, card)
                    if job and job['link'] and job['link'] not in seen:
                        seen.add(job['link'])
                        all_jobs.append(job)
                        print(f"    [{len(all_jobs)}] {job['company']}: {job['title'][:40]}...")

            except Exception as e:
                print(f"  Error: {e}")

        await browser.close()

    # Save results
    if all_jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_file = OUTPUT_DIR / f"yc_jobs_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)

        md_file = OUTPUT_DIR / f"yc_jobs_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# Y Combinator Startup Jobs\n\n")
            f.write(f"*Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
            f.write(f"*Total Jobs: {len(all_jobs)}*\n\n")
            f.write("---\n\n")

            for i, job in enumerate(all_jobs, 1):
                f.write(f"## {i}. {job['title']}\n\n")
                f.write(f"**Company:** {job['company']}\n\n")
                f.write(f"**Location:** {job['location']}\n\n")
                f.write(f"**Link:** {job['link']}\n\n")
                f.write("---\n\n")

        print(f"\nSaved {len(all_jobs)} jobs to {json_file}")

    return all_jobs


if __name__ == "__main__":
    asyncio.run(scrape_yc())
