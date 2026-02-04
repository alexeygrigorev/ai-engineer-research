#!/usr/bin/env python3
"""Debug script to find correct selectors for job sites."""
import os
import time
import asyncio
import sys
from dotenv import load_dotenv
from playwright.async_api import async_playwright

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

TEST_URLS = {
    "Built In Berlin": "https://builtin.com/jobs/eu/germany/berlin/dev-engineering/search/artificial-intelligence",
    "YC Work at Startup": "https://workatastartup.com/jobs?role=engineering&q=ai",
    "Built In London": "https://builtinlondon.uk/jobs/dev-engineering/search/ai-engineer",
}


async def debug_page(url: str, name: str):
    """Load a page and dump its structure."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")

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

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"[OK] Page loaded")

            # Check for common job selectors
            selectors_to_try = [
                "div.job-item",
                "[data-test='job-item']",
                "a[href*='/job/']",
                ".job-listing",
                "[class*='job']",
                "article",
                "h3",
            ]

            found = []
            for selector in selectors_to_try:
                try:
                    count = len(await page.query_selector_all(selector))
                    if count > 0:
                        found.append((selector, count))
                        print(f"  [OK] Found {count} elements with: {selector}")
                except:
                    pass

            if not found:
                print("\n  No job elements found. Dumping page structure...")
                # Get all class names on the page
                class_names = await page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('*[class]');
                        const classes = new Set();
                        all.forEach(el => {
                            el.classList.forEach(c => classes.add(c));
                        });
                        return Array.from(classes).filter(c => c.toLowerCase().includes('job')).slice(0, 20);
                    }
                """)
                if class_names:
                    print(f"  Job-related class names: {class_names}")

                # Get all link hrefs
                links = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.map(a => a.href).filter(h => h.includes('/job/')).slice(0, 10);
                    }
                """)
                if links:
                    print(f"\n  Sample job links:")
                    for link in links[:5]:
                        print(f"    {link}")

        except Exception as e:
            print(f"[ERROR] {e}")

        finally:
            await browser.close()


async def main():
    print("="*60)
    print("Job Site Selector Debugger")
    print("="*60)

    for name, url in TEST_URLS.items():
        await debug_page(url, name)


if __name__ == "__main__":
    asyncio.run(main())
