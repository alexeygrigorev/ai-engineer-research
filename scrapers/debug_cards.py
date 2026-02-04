#!/usr/bin/env python3
"""Debug script to check what's on the page."""
import os
import time
import asyncio
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

TEST_URL = "https://www.builtinla.com/jobs?search=AI+engineer&allLocations=true"


async def main():
    print("Testing page load...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser to see what's happening
            proxy=PROXY_CONFIG,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        print(f"Fetching: {TEST_URL}")
        response = await page.goto(TEST_URL, wait_until="networkidle", timeout=60000)
        print(f"Status: {response.status}")

        # Wait for content to load
        await asyncio.sleep(10)

        # Check for various elements
        checks = await page.evaluate("""
            () => {
                const results = {};

                // Check for job cards
                results['jobCards_data-id'] = document.querySelectorAll('div[id^="job-card-"]').length;
                results['jobCards_class'] = document.querySelectorAll('div.job-bounded-responsive').length;

                // Check for any job links
                results['job_links'] = document.querySelectorAll('a[href*="/job/"]').length;

                // Check for h2/h3 headings
                results['h2'] = document.querySelectorAll('h2').length;
                results['h3'] = document.querySelectorAll('h3').length;

                // Get page title
                results['pageTitle'] = document.title;

                // Get first few h2/h3 texts
                const headings = [];
                document.querySelectorAll('h2, h3').forEach(h => {
                    if (headings.length < 5) {
                        headings.push(h.textContent?.trim().substring(0, 100));
                    }
                });
                results['sampleHeadings'] = headings;

                // Get body text length
                results['bodyLength'] = document.body.innerText.length;

                return results;
            }
        """)

        for key, value in checks.items():
            print(f"  {key}: {value}")

        # Save HTML for inspection
        html = await page.content()
        with open("../jobs/debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\nSaved HTML to jobs/debug_page.html")

        print("\nPress Enter to close...")
        input()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
