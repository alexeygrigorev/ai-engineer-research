#!/usr/bin/env python3
"""
Job scraper using Playwright with Oxylabs proxy.
Supports: Wellfound, Built In, Y Combinator
"""
import os
import re
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page

load_dotenv()

# Oxylabs proxy configuration
OXYLABS_ENDPOINT = os.getenv("OXYLABS_ENDPOINT", "pr.oxylabs.io:7777")
OXYLABS_USER = os.getenv("OXYLABS_USER")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")

# Build session-based proxy URL (rotating proxy)
PROXY_SERVER = f"http://{OXYLABS_ENDPOINT}"
PROXY_USERNAME = f"customer-{OXYLABS_USER}-sessid-{int(time.time())}-sesstime-10"
PROXY_CONFIG = {
    "server": PROXY_SERVER,
    "username": PROXY_USERNAME,
    "password": OXYLABS_PASSWORD,
}

OUTPUT_DIR = Path("jobs_raw")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================
# JOB BOARD CONFIGURATIONS
# ============================================

JOB_BOARDS = {
    "wellfound_us": {
        "name": "Wellfound (US)",
        "base_url": "https://wellfound.com/role/l/artificial-intelligence-engineer/united-states",
        "pages": 3,
        "selector": "div.styles_item__LiWNS",  # Job card selector
    },
    "wellfound_uk": {
        "name": "Wellfound (UK)",
        "base_url": "https://wellfound.com/role/l/artificial-intelligence-engineer/united-kingdom",
        "pages": 2,
        "selector": "div.styles_item__LiWNS",
    },
    "wellfound_eu": {
        "name": "Wellfound (Europe)",
        "base_url": "https://wellfound.com/role/l/ai-engineer/europe",
        "pages": 3,
        "selector": "div.styles_item__LiWNS",
    },
    "builtin_berlin": {
        "name": "Built In Berlin",
        "base_url": "https://builtin.com/jobs/eu/germany/berlin/dev-engineering/search/artificial-intelligence",
        "pages": 3,
        "selector": "div.job-item",
    },
    "builtin_london": {
        "name": "Built In London",
        "base_url": "https://builtinlondon.uk/jobs/dev-engineering/search/ai-engineer",
        "pages": 3,
        "selector": "div.job-item",
    },
    "yc_startups": {
        "name": "Y Combinator Work at a Startup",
        "base_url": "https://workatastartup.com/jobs?role=engineering&q=ai+machine+learning",
        "pages": 2,
        "selector": "a.job-item",
    },
}


# ============================================
# SCRAPER FUNCTIONS
# ============================================

async def extract_wellfound_job(page: Page, job_element) -> dict:
    """Extract job details from a Wellfound job card."""
    try:
        title_elem = await job_element.query_selector("h2.styles_title__k3Gai")
        company_elem = await job_element.query_selector("div.styles_info__HElGO a")
        location_elem = await job_element.query_selector("div.styles_location__sT4vV")
        link_elem = await job_element.query_selector("a")

        title = await title_elem.inner_text() if title_elem else "N/A"
        company = await company_elem.inner_text() if company_elem else "N/A"
        location = await location_elem.inner_text() if location_elem else "N/A"
        link = await link_elem.get_attribute("href") if link_elem else ""

        if link and not link.startswith("http"):
            link = urljoin("https://wellfound.com", link)

        # Extract salary if present
        salary_elem = await job_element.query_selector("div.styles_salary__K_zdU")
        salary = await salary_elem.inner_text() if salary_elem else ""

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "salary": salary.strip(),
            "link": link,
            "source": "wellfound",
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"  Error extracting Wellfound job: {e}")
        return None


async def extract_builtin_job(page: Page, job_element) -> dict:
    """Extract job details from a Built In job card."""
    try:
        title_elem = await job_element.query_selector("h3, h2")
        company_elem = await job_element.query_selector(".company-name, a.company-link")
        location_elem = await job_element.query_selector(".location, .job-location")
        link_elem = await job_element.query_selector("a")

        title = await title_elem.inner_text() if title_elem else "N/A"
        company = await company_elem.inner_text() if company_elem else "N/A"
        location = await location_elem.inner_text() if location_elem else "N/A"
        link = await link_elem.get_attribute("href") if link_elem else ""

        if link and not link.startswith("http"):
            base_url = f"{'https://builtin.com' if 'builtin.com' in link else 'https://builtinlondon.uk'}"
            link = urljoin(base_url, link)

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "salary": "",
            "link": link,
            "source": "builtin",
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"  Error extracting Built In job: {e}")
        return None


async def extract_yc_job(page: Page, job_element) -> dict:
    """Extract job details from Y Combinator job card."""
    try:
        title_elem = await job_element.query_selector("h2, h3")
        company_elem = await job_element.query_selector(".company-name")
        location_elem = await job_element.query_selector(".location")

        title = await title_elem.inner_text() if title_elem else "N/A"
        company = await company_elem.inner_text() if company_elem else "N/A"
        location = await location_elem.inner_text() if location_elem else "Remote"
        link = await job_element.get_attribute("href") if isinstance(job_element, Page) else ""

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "salary": "",
            "link": link,
            "source": "ycombinator",
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"  Error extracting YC job: {e}")
        return None


# ============================================
# MAIN SCRAPER
# ============================================

async def scrape_board(board_id: str, board_config: dict):
    """Scrape a single job board."""
    jobs = []
    board_name = board_config["name"]
    base_url = board_config["base_url"]
    num_pages = board_config["pages"]
    selector = board_config["selector"]

    print(f"\n{'='*60}")
    print(f"Scraping: {board_name}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        # Use proxy for all sites
        proxy_config = PROXY_CONFIG
        print(f"Using proxy: {OXYLABS_ENDPOINT}")
        print(f"Username: {PROXY_USERNAME}")

        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_config,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        )

        # Add stealth scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)

        page = await context.new_page()

        # Determine extractor function
        if "wellfound" in board_id:
            extract_func = extract_wellfound_job
        elif "builtin" in board_id:
            extract_func = extract_builtin_job
        elif "yc" in board_id:
            extract_func = extract_yc_job
        else:
            extract_func = extract_builtin_job

        for page_num in range(1, num_pages + 1):
            try:
                url = base_url
                if page_num > 1 and "wellfound" in board_id:
                    url = f"{base_url}?page={page_num}"
                elif page_num > 1:
                    url = f"{base_url}?page={page_num}"

                print(f"\n  Page {page_num}/{num_pages}: {url}")

                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                if response.status != 200:
                    print(f"    Warning: Got status {response.status}")
                    continue

                # Wait for job listings to load
                await page.wait_for_selector(selector, timeout=10000)

                # Scroll to load all items
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # Get all job cards
                job_cards = await page.query_selector_all(selector)
                print(f"    Found {len(job_cards)} job cards")

                for i, card in enumerate(job_cards):
                    job = await extract_func(page, card)
                    if job:
                        jobs.append(job)
                        print(f"      [{i+1}] {job['company']}: {job['title'][:40]}...")

                # Random delay between pages
                await asyncio.sleep(3)

            except Exception as e:
                print(f"    Error on page {page_num}: {e}")
                continue

        await browser.close()

    # Save results
    if jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"{board_id}_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

        # Also save as markdown
        md_file = OUTPUT_DIR / f"{board_id}_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# {board_name} Jobs\n\n")
            f.write(f"*Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
            f.write(f"*Total: {len(jobs)} jobs*\n\n")
            f.write("---\n\n")

            for i, job in enumerate(jobs, 1):
                f.write(f"## {i}. {job['title']}\n\n")
                f.write(f"**Company:** {job['company']}\n\n")
                f.write(f"**Location:** {job['location']}\n\n")
                if job['salary']:
                    f.write(f"**Salary:** {job['salary']}\n\n")
                f.write(f"**Link:** {job['link']}\n\n")
                f.write("---\n\n")

        print(f"\n  Saved {len(jobs)} jobs to {output_file}")
        print(f"  Also saved as markdown to {md_file}")

    return jobs


async def main():
    """Main entry point."""
    print("="*60)
    print("Job Scraper with Playwright + Oxylabs Proxy")
    print("="*60)

    # Parse command line arguments
    import sys
    boards_to_scrape = sys.argv[1:] if len(sys.argv) > 1 else list(JOB_BOARDS.keys())

    all_jobs = []
    for board_id in boards_to_scrape:
        if board_id not in JOB_BOARDS:
            print(f"Unknown board: {board_id}")
            continue

        board_config = JOB_BOARDS[board_id]
        jobs = await scrape_board(board_id, board_config)
        all_jobs.extend(jobs)

    # Summary
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total jobs scraped: {len(all_jobs)}")

    # Save combined results
    if len(all_jobs) > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_file = OUTPUT_DIR / f"all_jobs_{timestamp}.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        print(f"Combined results: {combined_file}")


if __name__ == "__main__":
    asyncio.run(main())
