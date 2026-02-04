#!/usr/bin/env python3
"""Test Berlin Built In job extraction."""
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

# Berlin page 2 URL as provided by user
TEST_URL = "https://builtin.com/jobs?search=AI%20Engineer&city=Berlin&state=Berlin&country=DEU&allLocations=true&page=2"


async def main():
    print(f"Testing Berlin Built In job extraction...")
    print(f"URL: {TEST_URL}\n")

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

        print("Loading page...")
        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Wait for job cards
        await page.wait_for_selector('h2 a[href*="/job/"]', timeout=15000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        # Extract job data
        jobs = await page.evaluate('''
            () => {
                const results = [];

                // Find all job title links
                const titleLinks = document.querySelectorAll('h2 a[href*="/job/"]');

                console.log('Found job title links:', titleLinks.length);

                for (const titleLink of titleLinks) {
                    const result = {};

                    // Title and Link
                    result.title = titleLink.textContent.trim();
                    result.link = titleLink.href;

                    // Find company link - look for nearest a[href*="/company"]
                    let companyLink = titleLink.closest('div')?.querySelector('a[href*="/company"]');
                    if (!companyLink) {
                        // Try parent's siblings
                        const parent = titleLink.closest('div');
                        if (parent) {
                            const grandparent = parent.parentElement;
                            if (grandparent) {
                                companyLink = grandparent.querySelector('a[href*="/company"]');
                            }
                        }
                    }

                    if (companyLink) {
                        // Try to get company name from image alt attribute
                        const img = companyLink.querySelector('img[data-id="company-img"]');
                        if (img && img.alt) {
                            // Alt is like "NVIDIA Logo" - extract just the name
                            result.company = img.alt.replace(' Logo', '').replace(' logo', '').trim();
                        } else {
                            // Fallback to text content
                            const span = companyLink.querySelector('span');
                            result.company = span ? span.textContent.trim() : companyLink.textContent.trim();
                        }
                    } else {
                        result.company = 'NOT_FOUND';
                    }

                    // Find parent card for other fields - try multiple approaches
                    let card = titleLink.closest('div[id^="job-card-"]') ||
                               titleLink.closest('.job-bounded-responsive') ||
                               titleLink.closest('[class*="job"]') ||
                               titleLink.closest('div').parentElement;

                    if (card) {
                        // Location (fa-location-dot)
                        const locIcon = card.querySelector('.fa-location-dot');
                        if (locIcon) {
                            // Try multiple parent levels
                            let parent = locIcon.parentElement;
                            while (parent && parent !== card) {
                                const text = parent.textContent.replace(/\\s+/g, ' ').trim();
                                if (text && text.length < 100 && !text.includes('NVIDIA')) {
                                    // Remove icon class text if present
                                    result.location = text.replace(/fa-location-dot/g, '').trim();
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        }

                        // Work type (fa-house-building)
                        const typeIcon = card.querySelector('.fa-house-building');
                        if (typeIcon) {
                            let parent = typeIcon.parentElement;
                            while (parent && parent !== card) {
                                const text = parent.textContent.replace(/\\s+/g, ' ').trim();
                                if (text && text.length < 50 && !text.includes('NVIDIA')) {
                                    result.work_type = text.replace(/fa-house-building/g, '').trim();
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        }

                        // Salary (fa-sack-dollar)
                        const salaryIcon = card.querySelector('.fa-sack-dollar');
                        if (salaryIcon) {
                            let parent = salaryIcon.parentElement;
                            while (parent && parent !== card) {
                                const text = parent.textContent.replace(/\\s+/g, ' ').trim();
                                if (text && text.length < 50 && !text.includes('NVIDIA')) {
                                    result.compensation = text.replace(/fa-sack-dollar/g, '').trim();
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        }

                        // Level (fa-trophy)
                        const levelIcon = card.querySelector('.fa-trophy');
                        if (levelIcon) {
                            let parent = levelIcon.parentElement;
                            while (parent && parent !== card) {
                                const text = parent.textContent.replace(/\\s+/g, ' ').trim();
                                if (text && text.length < 50 && !text.includes('NVIDIA')) {
                                    result.level = text.replace(/fa-trophy/g, '').trim();
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        }
                    }

                    results.push(result);
                }

                return results;
            }
        ''')

        print(f"Extracted {len(jobs)} jobs:\n")

        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.get('company', 'N/A')}: {job.get('title', 'N/A')}")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   Type: {job.get('work_type', 'N/A')}")
            print(f"   Level: {job.get('level', 'N/A')}")
            print(f"   Compensation: {job.get('compensation', 'N/A')}")
            print(f"   Link: {job.get('link', 'N/A')}")
            print()

        await browser.close()

        print(f"\nTotal: {len(jobs)} jobs")


if __name__ == "__main__":
    asyncio.run(main())
