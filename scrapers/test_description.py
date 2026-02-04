#!/usr/bin/env python3
"""Test HTML to Markdown conversion for job descriptions."""
import os
import time
import asyncio
import re
from playwright.async_api import async_playwright
from html.parser import HTMLParser

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

TEST_URL = "https://builtin.com/job/ai-engineering-intern/7208499"


def html_to_markdown(html_content: str) -> str:
    """Better HTML to Markdown conversion."""
    if not html_content:
        return ""

    text = html_content

    # Handle bullet lists - convert before other processing
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1\n', text, flags=re.DOTALL)

    # Remove list containers
    text = re.sub(r'<ul[^>]*>|</ul>|<ol[^>]*>|</ol>', '', text)

    # Headers
    text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n\n## \2\n\n', text, flags=re.DOTALL)

    # Bold and italic
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    # Links
    text = re.sub(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    # Paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n', text, flags=re.DOTALL)

    # Breaks
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newline
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space

    # Remove common artifacts
    text = text.replace('\xa0', ' ')  # Non-breaking spaces
    text = text.replace('\\u200b', '')  # Zero-width spaces
    text = re.sub(r'\\\\1', '', text)  # Remove \1 artifacts
    text = re.sub(r'\\x1b\\[[0-9;]+m', '', text)  # ANSI escape codes

    # Clean up bullet points
    text = re.sub(r'^-\s*$', '', text, flags=re.MULTILINE)  # Empty bullets
    text = re.sub(r'\n+-\s*\n+', '\n', text)  # Consecutive empty lines with bullets

    return text.strip()


async def main():
    print("="*60)
    print("Testing HTML to Markdown conversion")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY_CONFIG,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        print(f"\nFetching: {TEST_URL}")
        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Get raw HTML description
        html_desc = await page.eval_on_selector(
            'div[id^="job-post-body-"].html-parsed-content',
            'el => el.innerHTML'
        )

        print(f"\nRaw HTML length: {len(html_desc)} characters")
        print(f"\n--- First 500 chars of HTML ---")
        print(html_desc[:500])

        # Convert to markdown
        markdown_desc = html_to_markdown(html_desc)

        print(f"\n--- Converted Markdown (first 1000 chars) ---")
        print(markdown_desc[:1000])

        # Save to file
        with open("../jobs/test_description.md", "w", encoding="utf-8") as f:
            f.write(markdown_desc)

        print(f"\nSaved to: jobs/test_description.md")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
