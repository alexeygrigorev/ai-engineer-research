#!/usr/bin/env python3
"""
Test extraction on one job - debug and fix extraction.
"""
import os
import time
import asyncio
import re
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

# Test job URLs - different job types to test
TEST_URLS = {
    "berlin_ai": "https://builtin.com/job/ai-engineer/8273513",
    "berlin_sre": "https://builtin.com/job/senior-site-reliability-engineer-ai-platform/8386931",
    "london_ai": "https://builtinlondon.uk/job/staff-machine-learning-engineer-ai-product-lab/4438582",
}


async def test_extraction(url: str, name: str):
    """Extract and show all data from one job page."""

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

        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"URL: {url}")
        print(f"{'='*60}")

        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        print(f"Status: {response.status}")

        await asyncio.sleep(3)

        # Dump raw page title
        page_title = await page.title()
        print(f"\nPage Title: {page_title}")

        # Try different extraction strategies
        print(f"\n--- EXTRACTION ATTEMPTS ---\n")

        # Attempt 1: Company from different selectors
        print("[1] Company extraction:")
        company_attempts = await page.evaluate("""
            () => {
                const results = [];

                // Method 1: Page title parts
                const titleParts = document.title.split('|');
                results.push(`Title parts: ${JSON.stringify(titleParts)}`);

                // Method 2: Company links
                const companyLinks = Array.from(document.querySelectorAll('a[href*="/company/"]'));
                results.push(`Company links found: ${companyLinks.length}`);
                companyLinks.forEach((link, i) => {
                    if (i < 3) {
                        results.push(`  Link ${i}: href="${link.href}" text="${link.textContent?.trim()}"`);
                    }
                });

                // Method 3: Looking for company name in body text
                const bodyText = document.body.innerText;
                const companyMatch = bodyText.match(/at\\s+([A-Z][A-Za-z\\s]+?)\\s+we're/i);
                if (companyMatch) results.push(`"at COMPANY" pattern: ${companyMatch[1]}`);

                // Method 4: Picture/alt text with logo
                const imgs = Array.from(document.querySelectorAll('img[alt*="Logo"]'));
                results.push(`Logo images: ${imgs.length}`);
                imgs.forEach((img, i) => {
                    if (i < 2) results.push(`  ${img.alt}`);
                });

                return results;
            }
        """)
        for line in company_attempts:
            print(f"  {line}")

        # Attempt 2: Location extraction
        print(f"\n[2] Location extraction:")
        location_attempts = await page.evaluate("""
            () => {
                const results = [];
                const bodyText = document.body.innerText;

                // Method 1: Look for "In-Office" or "Remote" patterns
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l);
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    if (line.includes('In-Office') || line.includes('Remote')) {
                        // Look at previous line for location
                        if (i > 0) {
                            results.push(`Line before: "${lines[i-1]}"`);
                        }
                        results.push(`Line with marker: "${line}"`);
                    }
                }

                // Method 2: Find "Attractive office in CITY"
                const officeMatch = bodyText.match(/Attractive office in\\s+([A-Z][a-z]+)/i);
                if (officeMatch) results.push(`"Attractive office in": ${officeMatch[1]}`);

                // Method 3: Find city name followed by comma and In-Office/Remote
                const cityMatch = bodyText.match(/([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?),\\s*(?:In-Office|Remote)/);
                if (cityMatch) results.push(`"City, In-Office": ${cityMatch[1]}`);

                // Method 4: Look for location icon and adjacent text
                const locIcon = document.querySelector('i.fa-location-dot, i.fa-map-location-dot');
                if (locIcon) {
                    const parent = locIcon.parentElement;
                    if (parent) results.push(`Location icon parent text: "${parent.textContent?.trim().substring(0, 100)}"`);
                }

                return results;
            }
        """)
        for line in location_attempts:
            print(f"  {line}")

        # Attempt 3: Get full structured data
        print(f"\n[3] Full structured extraction:")
        job_data = await page.evaluate("""
            () => {
                // Get title from h1
                const title = document.querySelector('h1')?.textContent?.trim() || '';

                // Company from company link - the one with just the company name
                let company = '';
                const companyLinks = Array.from(document.querySelectorAll('a[href*="/company/"]'));
                for (const link of companyLinks) {
                    const text = link.textContent?.trim();
                    // Find the link that's just the company name (no "View all" etc.)
                    if (text && text.length > 1 && text.length < 50 &&
                        !text.includes('View all') && !text.includes('jobs') &&
                        !link.href.includes('/jobs/')) {
                        company = text;
                        break;
                    }
                }

                // Fallback: extract from page title
                if (!company) {
                    const titleText = document.title;
                    const parts = titleText.split('|').map(p => p.trim());
                    if (parts.length >= 2) {
                        let companyPart = parts[parts.length - 2];
                        // Remove job title from company part
                        const jobTitle = parts[0];
                        if (companyPart.includes('-')) {
                            companyPart = companyPart.split('-').pop().trim();
                        }
                        company = companyPart;
                    }
                }

                // Get location - from page content or URL
                let location = '';
                const url = window.location.href;
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l);

                // Method 1: Look for "City, In-Office" pattern (on same line)
                for (const line of lines.slice(0, 30)) {
                    const match = line.match(/^([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?),\\s*(?:In-Office|Remote)/);
                    if (match) {
                        location = match[1];
                        break;
                    }
                }

                // Method 2: Look for city line before "In-Office" line
                if (!location) {
                    for (let i = 1; i < Math.min(30, lines.length); i++) {
                        if (lines[i] === 'In-Office' || lines[i] === 'Remote') {
                            // Check if previous line is a city
                            const knownCities = ['Berlin', 'London', 'Munich', 'Amsterdam', 'Paris', 'Hamburg', 'Frankfurt', 'Stuttgart', 'Cologne', 'New York', 'San Francisco'];
                            if (knownCities.includes(lines[i-1])) {
                                location = lines[i-1];
                                break;
                            }
                        }
                    }
                }

                // Method 3: Detect from URL path
                if (!location) {
                    if (url.includes('berlin') || url.includes('/eu/germany/berlin')) location = 'Berlin';
                    else if (url.includes('london') || url.includes('builtinlondon')) location = 'London';
                    else if (url.includes('amsterdam') || url.includes('/netherlands/')) location = 'Amsterdam';
                    else if (url.includes('munich')) location = 'Munich';
                    else if (url.includes('/eu/germany/')) location = 'Germany'; // Generic Germany location
                }

                // Method 4: Look for "Attractive office in CITY"
                if (!location) {
                    const officeMatch = bodyText.match(/Attractive office in\\s+([A-Z][a-z]+)/i);
                    if (officeMatch) location = officeMatch[1];
                }

                // Level and employment type
                let level = '';
                let empType = '';
                for (const line of lines.slice(0, 50)) {
                    if (/Entry level|Mid level|Senior level|Staff level|Principal level|Lead/.test(line)) {
                        level = line.match(/(Entry level|Mid level|Senior level|Staff level|Principal level|Lead)/)[0];
                    }
                    if (/Full-time|Part-time|Contract|Internship/.test(line)) {
                        empType = line.match(/(Full-time|Part-time|Contract|Internship)/)[0];
                    }
                }

                // Skills
                const skills = [];
                const allH2 = Array.from(document.querySelectorAll('h2'));
                const skillsH2 = allH2.find(h => h.textContent.includes('Top Skills'));
                if (skillsH2) {
                    const skillsContainer = skillsH2.closest('.bg-white');
                    if (skillsContainer) {
                        const skillEls = skillsContainer.querySelectorAll('.border.rounded-3');
                        skillEls.forEach(el => {
                            const text = el.textContent?.trim();
                            if (text && text.length > 1 && text.length < 30 &&
                                !text.includes('Upload') && !text.includes('Upload') &&
                                text.split(/(?=[A-Z])/).length < 10) {  // Not too many capitalized words
                                skills.push(text);
                            }
                        });
                    }
                }

                // Description
                const descContainer = document.querySelector('div[id^="job-post-body-"].html-parsed-content');
                const description = descContainer ? descContainer.innerHTML : '';

                return {
                    title: title,
                    company: company,
                    location: location,
                    level: level,
                    employment_type: empType,
                    skills: skills,
                    description_length: description.length,
                    url: window.location.href
                };
            }
        """)
        for key, value in job_data.items():
            if key == 'skills':
                print(f"  {key}: {', '.join(value)}")
            else:
                print(f"  {key}: {value}")

        await browser.close()


async def main():
    print("="*60)
    print("Job Extraction Debug")
    print("="*60)

    for name, url in TEST_URLS.items():
        await test_extraction(url, name)


if __name__ == "__main__":
    asyncio.run(main())
