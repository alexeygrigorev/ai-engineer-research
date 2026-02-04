#!/usr/bin/env python3
"""
Job scraper using Playwright with Oxylabs proxy.
Built In sites only (working).
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

# Fix Windows encoding
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


JOB_BOARDS = {
    "builtin_berlin": {
        "name": "Built In Berlin - AI/ML",
        "url": "https://builtin.com/jobs/eu/germany/berlin/dev-engineering/search/artificial-intelligence",
        "pages": 3,
    },
    "builtin_london": {
        "name": "Built In London - AI Engineer",
        "url": "https://builtinlondon.uk/jobs/dev-engineering/search/ai-engineer",
        "pages": 3,
    },
    "builtin_la": {
        "name": "Built In LA - AI",
        "url": "https://www.builtinla.com/jobs/artificial-intelligence",
        "pages": 2,
    },
    "builtin_amsterdam": {
        "name": "Built In Amsterdam - AI",
        "url": "https://builtin.com/jobs/eu/netherlands/amsterdam/dev-engineering/search/artificial-intelligence",
        "pages": 2,
    },
}


async def extract_builtin_job(page: Page, link_element) -> dict:
    """Extract job details from a Built In job link element."""
    try:
        # Get the link
        link = await link_element.get_attribute("href") or ""
        if link and not link.startswith("http"):
            if "builtinlondon" in link or "builtin.com" in link:
                link = urljoin("https://builtin.com", link)

        # Get the job card container (parent with job-related class)
        job_card = await link_element.evaluate_handle("""
            el => {
                let current = el;
                while (current && current !== document.body) {
                    if (current.className && typeof current.className === 'string' &&
                        current.className.includes('job')) {
                        return current;
                    }
                    current = current.parentElement;
                }
                return el.closest('div');
            }
        """)

        # Extract text content from the card
        card_text = await job_card.evaluate("el => el.textContent")

        # Extract title - usually the link text or from an h3/h2
        title_elem = await job_card.query_selector("h3, h2")
        title = ""
        if title_elem:
            title = await title_elem.inner_text()
        else:
            # Get link text as fallback
            title = await link_element.inner_text()

        # Try to find company and location from the card
        # Use JavaScript to get all text and parse it
        card_info = await job_card.evaluate("""
            el => {
                const text = el.textContent;
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);

                // Company often appears before "—" or is first non-title line
                let company = "";
                let location = "";

                // Look for patterns
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    if (line.includes('—') || line.includes('-')) {
                        const parts = line.split(/—|-/);
                        if (parts.length >= 2) {
                            company = parts[0].trim();
                            location = parts[1].trim();
                        }
                    }
                    // Check for location keywords
                    if (line.match(/Remote|Berlin|Germany|London|UK|US|Amsterdam|Paris|Munich/i)) {
                        location = line;
                    }
                }

                return { company, location, lines: lines.slice(0, 5) };
            }
        """)

        company = card_info.get("company", "")
        location = card_info.get("location", "")

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "link": link,
            "source": "builtin",
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"      Error extracting job: {e}")
        return None


async def scrape_builtin_board(board_id: str, board_config: dict, save_debug: bool = False):
    """Scrape a Built In job board."""
    jobs = []
    board_name = board_config["name"]
    base_url = board_config["url"]
    num_pages = board_config["pages"]

    print(f"\n{'='*60}")
    print(f"Scraping: {board_name}")
    print(f"URL: {base_url}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY_CONFIG,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        for page_num in range(1, num_pages + 1):
            try:
                url = base_url
                if page_num > 1:
                    url = f"{base_url}?page={page_num}"

                print(f"\n  Page {page_num}/{num_pages}")

                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                if response.status != 200:
                    print(f"    Status: {response.status}")
                    continue

                # Save debug HTML if requested
                if save_debug and page_num == 1:
                    debug_file = OUTPUT_DIR / f"{board_id}_debug.html"
                    await page.save_debug_snapshot(str(debug_file))
                    print(f"    Saved debug snapshot to {debug_file}")

                # Wait for job links to load
                await page.wait_for_selector("a[href*='/job/']", timeout=15000)

                # Scroll to load all items
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(0.5)

                # Get all job links
                job_links = await page.query_selector_all("a[href*='/job/']")
                print(f"    Found {len(job_links)} job links")

                seen_titles = set()
                for link_elem in job_links:
                    job = await extract_builtin_job(page, link_elem)
                    if job and job['title']:
                        # Skip exact duplicates within page
                        key = f"{job['company']}|{job['title']}"
                        if key not in seen_titles:
                            seen_titles.add(key)
                            jobs.append(job)
                            print(f"      [{len(jobs)}] {job['company']}: {job['title'][:40]}...")

                await asyncio.sleep(2)

            except Exception as e:
                print(f"    Error: {e}")
                continue

        await browser.close()

    # Save results
    if jobs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = OUTPUT_DIR / f"{board_id}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved {len(jobs)} jobs to {json_file}")

        # Save as Markdown
        md_file = OUTPUT_DIR / f"{board_id}_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# {board_name}\n\n")
            f.write(f"*Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
            f.write(f"*Source: {base_url}*\n")
            f.write(f"*Total Jobs: {len(jobs)}*\n\n")
            f.write("---\n\n")

            for i, job in enumerate(jobs, 1):
                f.write(f"## {i}. {job['title']}\n\n")
                f.write(f"**Company:** {job['company']}\n\n")
                f.write(f"**Location:** {job['location']}\n\n")
                f.write(f"**Link:** {job['link']}\n\n")
                f.write("---\n\n")

        print(f"  Also saved markdown to {md_file}")

    return jobs


async def main():
    print("="*60)
    print("Built In Job Scraper")
    print("Using Oxylabs proxy")
    print("="*60)

    import sys
    boards = sys.argv[1:] if len(sys.argv) > 1 else ["builtin_berlin"]

    all_jobs = []
    for board_id in boards:
        if board_id not in JOB_BOARDS:
            print(f"Unknown board: {board_id}")
            print(f"Available: {', '.join(JOB_BOARDS.keys())}")
            continue

        board_config = JOB_BOARDS[board_id]
        jobs = await scrape_builtin_board(board_id, board_config, save_debug=(board_id == boards[0]))
        all_jobs.extend(jobs)

    # Summary
    print(f"\n{'='*60}")
    print(f"COMPLETE - {len(all_jobs)} total jobs scraped")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
