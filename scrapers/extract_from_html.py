#!/usr/bin/env python3
"""Extract job data from raw HTML files and save as YAML."""
import json
import re
import html
import yaml
from pathlib import Path
from bs4 import BeautifulSoup

# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR = PROJECT_ROOT / "jobs" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "jobs" / "extracted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_from_json_ld(html_content):
    """Extract job data from JSON-LD script tag using BeautifulSoup."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all script tags with type containing ld+json (with or without HTML entity)
    # BeautifulSoup handles HTML entity decoding automatically
    script_tags = soup.find_all('script', type=lambda x: x and 'ld' in x and 'json' in x)

    for script in script_tags:
        if not script.string:
            continue

        json_str = script.string.strip()

        # Unescape any HTML entities (e.g., &#x2B; -> +)
        json_str = html.unescape(json_str)

        try:
            data = json.loads(json_str)

            # Handle @graph wrapper
            if isinstance(data, dict) and '@graph' in data:
                data = data['@graph']
            elif isinstance(data, dict):
                data = [data]

            # Find JobPosting
            for item in data:
                if item.get('@type') == 'JobPosting':
                    return item
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def extract_skills(soup):
    """Extract skills from Top Skills section."""
    skills = []
    all_h2 = soup.find_all('h2')
    for h2 in all_h2:
        if 'Top Skills' in h2.get_text():
            skills_container = h2.find_next(['div', 'section'])
            if skills_container:
                skill_elements = skills_container.find_all(['div', 'span', 'a'],
                    class_=re.compile(r'border|rounded|skill|tag', re.I))
                for el in skill_elements:
                    text = el.get_text().strip()
                    if text and 1 < len(text) < 40:
                        if not any(x in text.lower() for x in ['upload', 'apply', 'view all']):
                            if text not in skills:
                                skills.append(text)
    return skills[:10]


def extract_company_size(html_text):
    """Extract company size from text."""
    match = re.search(r'(\d+[,\d]*)\s+Employees', html_text)
    if match:
        return match.group(1) + ' Employees'
    return ''


def months_to_level(months):
    """Convert months of experience to level string."""
    if not months:
        return ''
    years = months / 12
    if years < 2:
        return 'Entry level'
    elif years < 4:
        return 'Mid level'
    elif years < 7:
        return 'Senior level'
    else:
        return 'Expert/Leader'


def html_to_markdown(html_content):
    """Convert HTML description to clean Markdown."""
    if not html_content:
        return ""

    text = html_content
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<ul[^>]*>|</ul>|<ol[^>]*>|</ol>', '', text)
    text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n\n## \2\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.replace('\xa0', ' ')
    text = text.replace('\u200b', '')
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return text.strip()


def extract_job_data(html_file):
    """Extract all job data from raw HTML file."""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    job = {
        'job_id': '',
        'title': '',
        'company': '',
        'location': '',
        'work_type': '',
        'level': '',
        'skills': [],
        'company_size': '',
        'compensation': '',
        'description': '',
        'benefits': '',
        'industries': [],
        'posted_date': '',
        'url': '',
        'source': 'Built In'
    }

    # JSON-LD extraction
    json_ld = extract_from_json_ld(html_content)
    if json_ld:
        job['title'] = json_ld.get('title', '')
        desc_html = json_ld.get('description', '')
        job['description'] = html_to_markdown(desc_html)

        org = json_ld.get('hiringOrganization', {})
        job['company'] = org.get('name', '')

        job_loc = json_ld.get('jobLocation', {})
        if isinstance(job_loc, dict):
            addr = job_loc.get('address', {})
            city = addr.get('addressLocality', '')
            country = addr.get('addressCountry', '')
            if city and country:
                job['location'] = f"{city}, {country}"
            elif city:
                job['location'] = city
            elif country:
                job['location'] = country

        job['work_type'] = json_ld.get('employmentType', '')
        job['benefits'] = json_ld.get('jobBenefits', '')

        base_salary = json_ld.get('baseSalary')
        if base_salary:
            if isinstance(base_salary, dict):
                value = base_salary.get('value', {})
                if isinstance(value, dict):
                    job['compensation'] = value.get('value', '')
                else:
                    job['compensation'] = str(value)
            else:
                job['compensation'] = str(base_salary)

        job['posted_date'] = json_ld.get('datePosted', '')

        exp = json_ld.get('experienceRequirements', {})
        if isinstance(exp, dict):
            months = exp.get('monthsOfExperience')
            job['level'] = months_to_level(months)

        industries = json_ld.get('industry', [])
        if isinstance(industries, list):
            job['industries'] = industries

        job['url'] = json_ld.get('url', '')

    # Fallback HTML parsing
    if not job['title']:
        h1 = soup.find('h1')
        if h1:
            job['title'] = h1.get_text().strip()

    if not job['company']:
        company_link = soup.find('a', href=lambda x: x and '/company/' in x)
        if company_link:
            job['company'] = company_link.get_text().strip()

    if not job['url']:
        canonical = soup.find('link', rel='canonical')
        if canonical:
            job['url'] = canonical.get('href', '')

    # Extract job_id from URL
    if job['url']:
        from urllib.parse import urlparse
        parsed = urlparse(job['url'])
        job['job_id'] = parsed.path.split('/')[-1]

    # Additional fields
    html_text = soup.get_text()

    if not job['skills']:
        job['skills'] = extract_skills(soup)

    if not job['company_size']:
        job['company_size'] = extract_company_size(html_text)

    return job


def sanitize_filename(name):
    """Sanitize name for use as filename."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name.strip('_')


def write_yaml_file(job, yaml_file):
    """Write job data to YAML file, skipping empty fields."""
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(f"job_id: {job['job_id']}\n")
        f.write(f"title: {job['title']}\n")
        f.write(f"company: {job['company']}\n")
        f.write(f"location: {job['location']}\n")
        if job['work_type']:
            f.write(f"work_type: {job['work_type']}\n")
        if job['level']:
            f.write(f"level: {job['level']}\n")
        if job['skills']:
            f.write(f"skills:\n")
            for skill in job['skills']:
                f.write(f"  - {skill}\n")
        if job['company_size']:
            f.write(f"company_size: {job['company_size']}\n")
        if job['compensation']:
            f.write(f"compensation: {job['compensation']}\n")
        if job['description']:
            f.write(f"description: |\n")
            for line in job['description'].split('\n'):
                f.write(f"  {line}\n")
        if job['industries']:
            f.write(f"industries:\n")
            for ind in job['industries']:
                f.write(f"  - {ind}\n")
        if job['posted_date']:
            f.write(f"posted_date: {job['posted_date']}\n")
        f.write(f"url: {job['url']}\n")
        f.write(f"source: {job['source']}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract jobs from raw HTML')
    parser.add_argument('html_file', nargs='?', help='Specific HTML file to process')
    parser.add_argument('--all', action='store_true', help='Process all HTML files')
    args = parser.parse_args()

    if args.html_file:
        # Process single file
        html_file = Path(args.html_file)
        if not html_file.exists():
            print(f"File not found: {html_file}")
            return

        job = extract_job_data(html_file)

        # Generate filename
        job_id = job.get('job_id', 'unknown')
        company = sanitize_filename(job['company'])
        title_slug = sanitize_filename(job['title'][:50])
        yaml_file = OUTPUT_DIR / f"{job_id}_{company}_{title_slug}.yaml"

        # Write YAML (skips empty fields)
        write_yaml_file(job, yaml_file)

        print(f"Saved: {yaml_file.name}")
        print(f"  Title: {job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Skills: {', '.join(job['skills'][:5])}")

    elif args.all:
        # Process all files
        html_files = list(RAW_DIR.glob("*.html"))
        print(f"Processing {len(html_files)} HTML files...\n")

        for html_file in html_files:
            job = extract_job_data(html_file)

            job_id = job.get('job_id', 'unknown')
            company = sanitize_filename(job['company']) if job['company'] else 'Unknown'
            title_slug = sanitize_filename(job['title'][:50])
            yaml_file = OUTPUT_DIR / f"{job_id}_{company}_{title_slug}.yaml"

            # Write YAML (skips empty fields)
            write_yaml_file(job, yaml_file)

            print(f"[{html_files.index(html_file)+1}/{len(html_files)}] {yaml_file.name}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
