#!/usr/bin/env python3
"""
Extract full job details from Built In job page.
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

# Test URL - Wolters Kluwer AI Engineer job
JOB_URL = "https://builtin.com/job/ai-engineer/8273513"


async def extract_builtin_job_details(url: str):
    """Extract full job details from Built In job URL."""

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

        print(f"Fetching: {url}")
        response = await page.goto(url, wait_until="networkidle", timeout=30000)

        if response.status != 200:
            print(f"Error: HTTP {response.status}")
            await browser.close()
            return None

        # Wait for content to load
        await asyncio.sleep(3)

        # Extract job details using JavaScript
        job_data = await page.evaluate("""
            () => {
                // Get job title
                const title = document.querySelector('h1')?.textContent?.trim() ||
                             document.title.split('|')[0].trim();

                // Get company name from page title (after the dash)
                let company = '';
                const titleParts = document.title.split('|');
                if (titleParts.length > 1) {
                    company = titleParts[titleParts.length - 1].trim();
                }

                // Also try finding company link
                if (!company || company === 'Built In') {
                    const companyLinks = Array.from(document.querySelectorAll('a[href*="/company/"]'));
                    for (const link of companyLinks) {
                        const text = link.textContent?.trim();
                        if (text && text.length > 2 && text.length < 50) {
                            company = text;
                            break;
                        }
                    }
                }

                // Get location from the job details
                let location = '';
                const bodyText = document.body.innerText;

                // Try to find in "Attractive office in..." pattern
                const officeMatch = bodyText.match(/Attractive office in\\s+([A-Z][a-z]+)/);
                if (officeMatch) {
                    location = officeMatch[1];
                }

                // Also try pattern like "Berlin, In-Office"
                const locMatch = bodyText.match(/([A-Z][a-z]+),\\s*(?:In-Office|Remote)/);
                if (locMatch && !location) {
                    location = locMatch[1];
                }

                // Get job description - the main content
                const descContainer = document.querySelector('div[id^="job-post-body-"].html-parsed-content');
                let description = '';
                if (descContainer) {
                    description = descContainer.innerHTML;
                }

                // Get top skills/tags - find the section and extract
                const skills = [];
                const allH2 = Array.from(document.querySelectorAll('h2'));
                const skillsH2 = allH2.find(h => h.textContent.includes('Top Skills'));
                if (skillsH2) {
                    const skillsContainer = skillsH2.closest('.bg-white');
                    if (skillsContainer) {
                        const skillEls = skillsContainer.querySelectorAll('.border.rounded-3');
                        skillEls.forEach(el => {
                            const text = el.textContent?.trim();
                            if (text && text.length > 1 && text.length < 30 && !text.includes('Upload')) {
                                skills.push(text);
                            }
                        });
                    }
                }

                // Get job level
                let level = '';
                const levelMatch = bodyText.match(/(Entry level|Mid level|Senior level|Staff level|Principal level|Lead)/i);
                if (levelMatch) {
                    level = levelMatch[1];
                }

                return {
                    title: title,
                    company: company,
                    location: location,
                    level: level,
                    skills: skills.slice(0, 15),
                    description: description,
                    url: window.location.href
                };
            }
        """)

        await browser.close()

        return job_data


async def main():
    job_data = await extract_builtin_job_details(JOB_URL)

    if job_data:
        print("\n" + "="*60)
        print("EXTRACTED JOB DATA")
        print("="*60)
        print(f"\nTitle: {job_data.get('title')}")
        print(f"Company: {job_data.get('company')}")
        print(f"Location: {job_data.get('location')}")
        print(f"Level: {job_data.get('level')}")
        print(f"\nSkills: {', '.join(job_data.get('skills', []))}")
        print(f"\nDescription length: {len(job_data.get('description', ''))} characters")

        # Save as markdown
        description_text = job_data.get('description', '')
        # Convert HTML to readable text
        description_text = re.sub(r'<[^>]+>', '\n', description_text)
        description_text = re.sub(r'\n+', '\n\n', description_text)
        description_text = description_text.strip()

        markdown = f"""# {job_data.get('title')}

**Company:** {job_data.get('company')}
**Location:** {job_data.get('location')}
**Level:** {job_data.get('level')}
**Source:** Built In
**URL:** {job_data.get('url')}

## Skills

{', '.join(job_data.get('skills', []))}

## Description

{description_text}
"""

        output_file = "../jobs/extracted_job.md"
        os.makedirs("../jobs", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"\nSaved to: {output_file}")
        print("\n--- First 500 chars of description ---")
        print(description_text[:500])


if __name__ == "__main__":
    asyncio.run(main())
