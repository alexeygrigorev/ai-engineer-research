#!/usr/bin/env python3
"""
Shared job extraction functions for Built In job scraper.
Can be used by both test scripts and the main scraper.
"""
import re
from playwright.async_api import Page


async def extract_builtin_job(page: Page) -> dict:
    """
    Extract complete job details from a Built In job page.

    Args:
        page: Playwright Page object with the job page loaded

    Returns:
        Dictionary with job details: title, company, location, level, employment_type,
        company_size, skills, description, url
    """
    job_data = await page.evaluate("""
        () => {
            // Get job title
            const title = document.querySelector('h1')?.textContent?.trim() ||
                         document.title.split('|')[0].trim();

            // Get company name from company link
            let company = '';
            const companyLinks = Array.from(document.querySelectorAll('a[href*="/company/"]'));
            for (const link of companyLinks) {
                const text = link.textContent?.trim();
                if (text && text.length > 1 && text.length < 50 &&
                    !text.includes('View all') && !text.includes('jobs') &&
                    !link.href.includes('/jobs/')) {
                    company = text;
                    break;
                }
            }

            // Get location, job type, and level from the specific HTML section
            // The section with icons: fa-location-dot (location), fa-house-building (type), fa-trophy (level)
            let location = '';
            let jobType = '';
            let level = '';

            // Location: find fa-location-dot icon and get adjacent span text
            const locIcon = document.querySelector('i.fa-location-dot, i.fa-map-location-dot');
            if (locIcon) {
                const parent = locIcon.closest('.d-flex');
                if (parent) {
                    const span = parent.querySelector('span.font-barlow');
                    if (span) {
                        location = span.textContent?.trim() || '';
                    }
                }
            }

            // Job Type: find fa-house-building icon (In-Office/Remote/Hybrid)
            const typeIcon = document.querySelector('i.fa-house-building, i.fa-building');
            if (typeIcon) {
                const parent = typeIcon.closest('.d-flex');
                if (parent) {
                    const span = parent.querySelector('span');
                    if (span) {
                        jobType = span.textContent?.trim() || '';
                    }
                }
            }

            // Level: find fa-trophy icon (Entry level/Mid level/Senior level/etc.)
            const levelIcon = document.querySelector('i.fa-trophy');
            if (levelIcon) {
                const parent = levelIcon.closest('.d-flex');
                if (parent) {
                    const span = parent.querySelector('span');
                    if (span) {
                        level = span.textContent?.trim() || '';
                    }
                }
            }

            // Fallback: scan body text for patterns
            if (!location) {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l);

                // Look for "City, In-Office" pattern
                for (let i = 1; i < Math.min(30, lines.length); i++) {
                    if (lines[i] === 'In-Office' || lines[i] === 'Remote') {
                        const knownCities = ['Berlin', 'London', 'Munich', 'Amsterdam', 'Paris', 'Hamburg', 'Frankfurt', 'Stuttgart', 'Cologne', 'New York', 'San Francisco'];
                        if (knownCities.includes(lines[i-1])) {
                            location = lines[i-1];
                            break;
                        }
                    }
                }

                // Try "Attractive office in CITY"
                if (!location) {
                    const officeMatch = bodyText.match(/Attractive office in\\s+([A-Z][a-z]+)/i);
                    if (officeMatch) location = officeMatch[1];
                }

                // Try URL detection
                if (!location) {
                    const url = window.location.href;
                    if (url.includes('berlin') || url.includes('/eu/germany/berlin')) location = 'Berlin';
                    else if (url.includes('london') || url.includes('builtinlondon')) location = 'London';
                    else if (url.includes('amsterdam') || url.includes('/netherlands/')) location = 'Amsterdam';
                    else if (url.includes('munich')) location = 'Munich';
                }
            }

            // Get job description
            const descContainer = document.querySelector('div[id^="job-post-body-"].html-parsed-content');
            const description = descContainer ? descContainer.innerHTML : '';

            // Get skills from Top Skills section
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
                            !text.includes('Upload') &&
                            text.split(/(?=[A-Z])/).length < 10) {  // Not too many capitalized words
                            skills.push(text);
                        }
                    });
                }
            }

            // Get company size
            let companySize = '';
            const bodyText = document.body.innerText;
            const sizeMatch = bodyText.match(/([\\d,]+)\\s+Employees/i);
            if (sizeMatch) {
                companySize = sizeMatch[1];
            }

            // Get compensation/salary
            let compensation = '';
            // Look for salary patterns in body text
            const salaryPatterns = [
                /[$€£¥]?[\\d,]+k?\\s*(?:-|to|\\/)\\s*[$€£¥]?[\\d,]+k?\\s*(?:per year|annual|salary)/i,
                /Salary:\\s*[$€£¥]?[\\d,]+k?/i,
                /[$€£¥]?[\\d,]+k?\\s*-\\s*[$€£¥]?[\\d,]+k?\\s*per year/i,
                /[$€£¥]?(\\d{2,3},?\\d{3})\\s*-\\s*[$€£¥]?(\\d{2,3},?\\d{3})\\s*k/i,
                /Competitive\\s+salary/i,
            ];
            for (const pattern of salaryPatterns) {
                const match = bodyText.match(pattern);
                if (match) {
                    compensation = match[0];
                    break;
                }
            }

            // Also check specific containers
            const salaryContainer = document.querySelector('[class*="salary"], [class*="compensation"], [class*="pay"]');
            if (salaryContainer) {
                const salaryText = salaryContainer.textContent?.trim();
                if (salaryText && salaryText.length < 100) {
                    compensation = salaryText;
                }
            }

            return {
                title: title || '',
                company: company || '',
                location: location || '',
                level: level || '',
                employment_type: jobType || '',
                company_size: companySize || '',
                compensation: compensation || '',
                skills: skills,
                description: description || '',
                url: window.location.href
            };
        }
        """)
    return job_data


def html_to_markdown(html_content: str) -> str:
    """
    Convert HTML description to clean Markdown.

    Args:
        html_content: Raw HTML string

    Returns:
        Clean markdown text
    """
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
    text = text.replace('\u200b', '')  # Zero-width spaces
    text = re.sub(r'&nbsp;', ' ', text)  # HTML non-breaking spaces
    text = re.sub(r'&amp;', '&', text)  # HTML ampersand
    text = re.sub(r'&lt;', '<', text)  # HTML less than
    text = re.sub(r'&gt;', '>', text)  # HTML greater than

    # Clean up bullet points
    text = re.sub(r'^-\s*$', '', text, flags=re.MULTILINE)  # Empty bullets
    text = re.sub(r'\n+-\s*\n+', '\n', text)  # Consecutive empty lines with bullets

    return text.strip()
