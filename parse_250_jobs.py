#!/usr/bin/env python3
"""Parse 250_jobs.html and extract ALL job postings with links."""

from bs4 import BeautifulSoup
import re
import html
from urllib.parse import urlparse
from collections import defaultdict

# Read the HTML file
html_file = r"C:\Users\alexe\git\ai-engineer-research\research_html\250_jobs.html"
print(f"Reading HTML file from: {html_file}")

with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

print(f"HTML content length: {len(html_content)} characters")

# Parse with BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# Extract all URLs from the raw content first
raw_urls = re.findall(r'https?://[^\s<>"\'()\{\}\|\\\^`\[\]]+', html_content)
print(f"\nRaw URLs found: {len(raw_urls)}")

# Clean and filter URLs
job_domains = {
    'wellfound.com',
    'indeed.com',
    'uk.indeed.com',
    'ie.indeed.com',
    'builtin.com',
    'builtinlondon.uk',
    'builtinla.com',
    'newgrad-jobs.com',
    'jobsinparis.fr',
    'jobs.ac.uk',
    'techjobs.co.uk',
    'gradcracker.com',
    'getclera.com',
    'totaljobs.com',
    'esa.int',
    'ellis.eu',
}

jobs_data = []
seen_urls = set()

# Extract all links using BeautifulSoup
all_links = soup.find_all('a', href=True)
print(f"Total <a> tags found: {len(all_links)}")

# Process all links
for link in all_links:
    href = link.get('href', '').strip()

    if not href or href.startswith('#') or href.startswith('javascript:'):
        continue

    # Clean up the URL
    href = href.split('\x00')[0]
    href = href.split('\n')[0]
    href = href.split('\r')[0]

    if len(href) > 500 or len(href) < 10:
        continue

    if href in seen_urls:
        continue

    # Get link text
    text = link.get_text(strip=True)
    title_attr = link.get('title', '')

    # Check if this is a job-related URL
    parsed = urlparse(href)
    domain = parsed.netloc.lower()

    # Include if it's from a known job domain
    is_job_domain = any(job_domain in domain for job_domain in job_domains)

    # Also check for job-related keywords in URL path
    path = parsed.path.lower()
    has_job_keywords = any(kw in path for kw in [
        '/job', '/jobs', '/career', '/careers', '/position',
        '/opening', '/role', '/posting', '/listing',
        '/viewjob', '/jvs/', '/company/jobs'
    ])

    if is_job_domain or has_job_keywords:
        seen_urls.add(href)

        # Try to extract structured info
        company = ''
        location = ''
        job_title = text or title_attr

        # Extract company from text
        if text:
            # Pattern: "Job Title at Company"
            at_match = re.search(r'at\s+([A-Z][A-Za-z0-9\s&.\-]+?)(?:\s*[-\|·]\s|\s+$|\s*\()', text)
            if at_match:
                company = at_match.group(1).strip()

            # Pattern: "Company - Job Title"
            if not company:
                dash_match = re.search(r'^([A-Z][A-Za-z0-9\s&.\-]+?)\s*[-\|·]\s+([A-Z])', text)
                if dash_match:
                    company = dash_match.group(1).strip()

            # Extract location
            loc_match = re.search(r'\b(?:Remote|Hybrid|On-site)(?:\s*,\s*[A-Z][A-Za-z]+)?\b', text)
            if loc_match:
                location = loc_match.group(0).strip()

        jobs_data.append({
            'title': job_title[:200] if job_title else 'Job Posting',
            'company': company[:100] if company else '',
            'location': location[:100] if location else '',
            'url': href,
            'domain': domain,
            'raw_text': text[:300] if text else ''
        })

print(f"\nJobs extracted from <a> tags: {len(jobs_data)}")

# If we still need more, parse raw URLs
if len(jobs_data) < 300:
    print("\nExtracting additional jobs from raw URLs...")

    for url in raw_urls:
        url = url.strip()
        if len(url) > 500 or len(url) < 15:
            continue

        # Clean URL
        url = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
        url = url.split('"')[0].split("'")[0].split('<')[0].split('>')[0]

        if url in seen_urls:
            continue

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check if it's a job-related URL
        is_job_domain = any(job_domain in domain for job_domain in job_domains)
        path = parsed.path.lower()
        has_job_keywords = any(kw in path for kw in [
            '/job', '/jobs', '/career', '/careers', '/position',
            '/viewjob', '/jvs/', '/company/jobs', '/role'
        ])

        if is_job_domain or has_job_keywords:
            seen_urls.add(url)
            jobs_data.append({
                'title': 'Job Posting',
                'company': '',
                'location': '',
                'url': url,
                'domain': domain,
                'raw_text': ''
            })

        if len(jobs_data) >= 500:
            break

print(f"\nTotal jobs extracted: {len(jobs_data)}")

# Remove duplicates based on URL
unique_jobs = []
seen = set()
for job in jobs_data:
    url_key = job['url'].split('?')[0].rstrip('/')
    if url_key not in seen:
        seen.add(url_key)
        unique_jobs.append(job)

print(f"After deduplication: {len(unique_jobs)}")

# Try to extract more info from HTML context
print("\nEnhancing job data with context...")

for job in unique_jobs[:300]:
    if not job['title'] or job['title'] == 'Job Posting':
        url_escaped = re.escape(job['url'][:50])
        context_match = re.search(r'.{0,300}' + url_escaped + r'.{0,300}', html_content, re.DOTALL)
        if context_match:
            context = context_match.group(0)
            # Look for job title patterns in JSON
            title_patterns = [
                r'"title"\s*:\s*"([^"]{10,80})"',
                r'"role"\s*:\s*"([^"]{10,80})"',
                r'"position"\s*:\s*"([^"]{10,80})"',
                r'"jobTitle"\s*:\s*"([^"]{10,80})"',
            ]
            for pattern in title_patterns:
                title_match = re.search(pattern, context)
                if title_match:
                    potential_title = title_match.group(1).strip()
                    if 10 < len(potential_title) < 100:
                        potential_title = html.unescape(potential_title)
                        if potential_title:
                            job['title'] = potential_title[:200]
                            break

# Sort by domain
unique_jobs.sort(key=lambda x: (x['domain'], x['url']))

# Group by domain
jobs_by_domain = defaultdict(list)
for job in unique_jobs:
    jobs_by_domain[job['domain']].append(job)

# Print summary
print(f"\nJobs by domain:")
for domain, jobs in sorted(jobs_by_domain.items(), key=lambda x: -len(x[1])):
    print(f"  {domain}: {len(jobs)}")

# Generate markdown output
md_lines = []
md_lines.append("# 250 AI Engineer Job Postings\n\n")
md_lines.append("*Source: AI Engineering Job Postings Aggregation*\n")
md_lines.append(f"*Total listings: {min(250, len(unique_jobs))}*\n\n")
md_lines.append("---\n\n")

domain_order = ['wellfound.com', 'indeed.com', 'uk.indeed.com', 'builtin.com',
                'builtinlondon.uk', 'builtinla.com', 'newgrad-jobs.com',
                'jobsinparis.fr', 'jobs.ac.uk', 'techjobs.co.uk']

for domain in domain_order:
    if domain not in jobs_by_domain:
        continue

for domain in jobs_by_domain:
    if domain not in domain_order:
        domain_order.append(domain)

job_count = 0
for domain in domain_order:
    if domain not in jobs_by_domain or job_count >= 250:
        continue

    jobs = jobs_by_domain[domain]
    if not jobs:
        continue

    md_lines.append(f"## {domain}\n\n")

    for job in jobs:
        if job_count >= 250:
            break
        job_count += 1

        # Format title
        title = job['title']
        title = html.unescape(title)
        title = re.sub(r'<[^>]+>', '', title)
        title = title.strip()

        if not title or title == 'Job Posting':
            url_path = urlparse(job['url']).path
            title = url_path.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            if not title or len(title) < 5:
                title = f"Job #{job_count}"

        md_lines.append(f"### {job_count}. {title}\n\n")

        if job['company']:
            md_lines.append(f"**Company:** {job['company']}\n\n")

        if job['location']:
            md_lines.append(f"**Location:** {job['location']}\n\n")

        md_lines.append(f"**Link:** {job['url']}\n\n")
        md_lines.append("---\n\n")

# Save markdown
md_file = r"C:\Users\alexe\git\ai-engineer-research\report\250_jobs.md"
with open(md_file, 'w', encoding='utf-8') as f:
    f.writelines(md_lines)

print(f"\nMarkdown file saved to: {md_file}")
print(f"Total jobs written: {job_count}")
