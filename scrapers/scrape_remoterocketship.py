#!/usr/bin/env python3
"""
RemoteRocketship job scraper - AI/ML remote jobs.
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


REMOTE_ROCKETSHIP_URLS = {
    "ai_eu": "https://www.remoterocketship.com/country/europe/jobs/ai-engineer/",
    "ai_uk": "https://www.remoterocketship.com/country/united-kingdom/jobs/ai-engineer/",
    "ai_us": "https://www.remoterocketship.com/country/united-states/jobs/ai-engineer/",
    "ml_eu": "https://www.remoterocketship.com/country/europe/jobs/machine-learning-engineer/",
    "ml_us": "https://www.remoterocketship.com/country/united-states/jobs/machine-learning-engineer/",
}


async def extract_rr_job(page: Page, job_card) -> dict:
    """Extract job from RemoteRocketship job card."""
    try:
        title_elem = await job_card.query_selector("h3, h2, .job-title, [class*='title']")
        company_elem = await job_card.query_selector(".company, [class*='company']")
        location_elem = await job_card.query_selector(".location, [class*='location']")

        title = await title_elem.inner_text() if title_elem else ""
        company = await company_elem.inner_text() if company_elem else ""
        location = await location_elem.inner_text() if location_elem else "Remote"

        link_elem = await job_card.query_selector("a[href]")
        link = await link_elem.get_attribute("href") if link_elem else ""
        if link and not link.startswith("http"):
            link = urljoin("https://www.remoterocketship.com", link)

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "link": link,
            "source": "remoterocketship",
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return None


async def scrape_remoterocketship():
    """Scrape RemoteRocketship jobs."""
    print("="*60)
    print("RemoteRocketship Job Scraper")
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

        for search_id, url in REMOTE_ROCKETSHIP_URLS.items():
            print(f"\nScraping: {search_id}")
            print(f"URL: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

                # Scroll to load all
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(0.5)

                # Find job cards
                selectors = [
                    "a[href*='/job/']",
                    "[class*='job']",
                    "article",
                ]

                job_cards = []
                for selector in selectors:
                    cards = await page.query_selector_all(selector)
                    if cards:
                        job_cards = cards
                        print(f"  Found {len(cards)} elements with: {selector}")
                        break

                seen = set()
                for card in job_cards:
                    job = await extract_rr_job(page, card)
                    if job and job['link'] and job['link'] not in seen:
                        seen.add(job['link'])
                        all_jobs.append(job)
                        print(f"    [{len(all_jobs)}] {job['company']}: {job['title'][:40]}...")

                await asyncio.sleep(2)

            except Exception as e:
                print(f"  Error: {e}")

        await browser.close()

    # Save results
    if all_jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_file = OUTPUT_DIR / f"rr_jobs_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)

        md_file = OUTPUT_DIR / f"rr_jobs_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# RemoteRocketship Jobs\n\n")
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
    asyncio.run(scrape_remoterocketship())
