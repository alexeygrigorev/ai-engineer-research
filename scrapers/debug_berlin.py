#!/usr/bin/env python3
"""Debug Berlin page structure."""
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

TEST_URL = "https://builtin.com/jobs?search=AI%20Engineer&city=Berlin&state=Berlin&country=DEU&allLocations=true&page=2"


async def main():
    print("Fetching Berlin page HTML for inspection...")

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

        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Check page structure
        checks = await page.evaluate('''
            () => {
                const results = {};

                // Check for various elements
                results['job_links'] = document.querySelectorAll('a[href*="/job/"]').length;
                results['company_links'] = document.querySelectorAll('a[href*="/company"]').length;
                results['h2'] = document.querySelectorAll('h2').length;
                results['h3'] = document.querySelectorAll('h3').length;
                results['fa-location-dot'] = document.querySelectorAll('.fa-location-dot').length;
                results['fa-house-building'] = document.querySelectorAll('.fa-house-building').length;
                results['fa-sack-dollar'] = document.querySelectorAll('.fa-sack-dollar').length;
                results['fa-trophy'] = document.querySelectorAll('.fa-trophy').length;

                // Get page title
                results['pageTitle'] = document.title;

                // Get sample job link HTML
                const jobLink = document.querySelector('a[href*="/job/"]');
                if (jobLink) {
                    results['sampleJobLinkHTML'] = jobLink.parentElement?.outerHTML?.substring(0, 500);
                }

                // Get sample company link HTML
                const companyLink = document.querySelector('a[href*="/company"]');
                if (companyLink) {
                    results['sampleCompanyLinkHTML'] = companyLink.outerHTML.substring(0, 500);
                }

                // Look for job cards
                results['jobCards'] = document.querySelectorAll('[class*="job"], [id*="job"]').length;

                return results;
            }
        ''')

        for key, value in checks.items():
            print(f"  {key}: {value}")

        # Save full HTML
        html = await page.content()
        output_path = "../jobs/berlin_page2.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nSaved HTML to {output_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
