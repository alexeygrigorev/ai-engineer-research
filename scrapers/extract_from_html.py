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


def html_to_markdown(html_content, wrap_width=60):
    """Convert HTML description to Markdown using BeautifulSoup."""
    if not html_content:
        return ""

    from bs4 import BeautifulSoup
    import textwrap

    soup = BeautifulSoup(html_content, 'html.parser')

    def process_list(ul, indent=0):
        """Process a list (ul or ol) and return markdown string."""
        prefix = '  ' * indent
        lines = []
        for li in ul.find_all('li', recursive=False):
            # Find nested list if any
            nested_list = li.find('ul') or li.find('ol')

            # Get text before nested list
            if nested_list:
                # Extract all nodes before the nested list
                label_nodes = []
                for child in li.children:
                    if child == nested_list:
                        break
                    label_nodes.append(child)

                # Build label from nodes
                label = ''
                for node in label_nodes:
                    if isinstance(node, str):
                        label += node.strip() + ' '
                    elif node.name not in ['ul', 'ol']:
                        label += node.get_text().strip() + ' '
            else:
                # No nested list, get all text
                label = li.get_text().strip()

            label = label.strip()
            # Fix spacing before colons
            label = re.sub(r'\s+:', ':', label)
            if label:
                lines.append(f"{prefix}- {label}")

            if nested_list:
                # Process nested list with increased indent
                nested_lines = process_list(nested_list, indent + 1)
                # Split and add each nested line
                for nested_line in nested_lines.split('\n'):
                    lines.append(nested_line)

        return '\n'.join(lines)

    # Process only top-level lists (not nested inside other lists)
    # Nested lists will be handled recursively by process_list
    all_lists = soup.find_all(['ul', 'ol'])
    top_level_lists = [ul for ul in all_lists if not ul.find_parent(['ul', 'ol'])]

    for ul in top_level_lists:
        md_list = process_list(ul)
        ul.replace_with('\n\n' + md_list + '\n\n')

    # Remove formatting tags
    for tag in soup.find_all(['strong', 'b', 'em', 'i', 'a']):
        tag.unwrap()

    # Convert block elements
    for tag in soup.find_all(['p', 'div']):
        tag.insert_before('\n\n')
        tag.insert_after('\n\n')
        tag.unwrap()

    for tag in soup.find_all('br'):
        tag.insert_before('\n')
        tag.unwrap()

    # Get text
    text = soup.get_text()

    # Clean up - preserve leading spaces for list indentation
    text = re.sub(r'\n\n\n+', '\n\n', text)  # Collapse excessive newlines
    # Collapse spaces within each line, but preserve leading spaces
    lines = []
    for line in text.split('\n'):
        # Count leading spaces
        leading_spaces = len(line) - len(line.lstrip(' \t'))
        # Collapse spaces in the rest of the line
        rest = re.sub(r'[ \t]+', ' ', line[leading_spaces:])
        lines.append(' ' * leading_spaces + rest)
    text = '\n'.join(lines)
    text = text.replace('\xa0', ' ')
    text = text.replace('\u200b', '')  # Zero-width space
    text = text.replace('\u2028', ' ')  # Line separator
    text = text.replace('\u2029', ' ')  # Paragraph separator
    text = text.replace('\u2003', ' ')  # Em space
    text = text.strip()

    # Wrap text at wrap_width characters (word-based, preserve list structure)
    wrapped_lines = []
    lines = text.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            wrapped_lines.append('')
            i += 1
        else:
            # Check if this is a list item (starts with optional spaces + dash)
            list_match = re.match(r'^(\s*)-(\s+)(.*)', line)
            if list_match:
                indent_spaces = list_match.group(1)  # Leading spaces before dash
                after_dash = list_match.group(2)  # Spaces after dash
                content = list_match.group(3)  # Actual content

                # Calculate indentation for continuation lines
                # Continuation should align with the content (indent spaces + dash + after_dash spaces)
                base_indent = len(indent_spaces) + 1 + len(after_dash)
                subsequent = ' ' * base_indent

                wrapped = textwrap.fill(content, width=wrap_width, initial_indent='', subsequent_indent=subsequent)

                # Build each line with proper prefix
                prefix = indent_spaces + '-' + after_dash
                wrapped_lines_list = wrapped.split('\n')
                for j, wrapped_line in enumerate(wrapped_lines_list):
                    if j == 0:
                        wrapped_lines.append(prefix + wrapped_line if wrapped_line else prefix.rstrip())
                    else:
                        wrapped_lines.append(wrapped_line if wrapped_line else '')
                i += 1
            else:
                # Regular paragraph - collect consecutive non-list lines
                para_text = line
                i += 1
                while i < len(lines) and not re.match(r'^\s*-', lines[i]) and lines[i].strip():
                    para_text += ' ' + lines[i].strip()
                    i += 1
                wrapped = textwrap.fill(para_text, width=wrap_width)
                wrapped_lines.extend(wrapped.split('\n'))

    text = '\n'.join(wrapped_lines)

    return text


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
    # Helper to safely quote YAML values (handles colons, special chars)
    def yaml_quote(s):
        if not s:
            return ''
        # Quote if contains special YAML characters
        if any(c in str(s) for c in [':', '[', ']', '{', '}', '|', '>', '#', '&']):
            # Use double quotes and escape internal quotes/backslashes
            quoted = str(s).replace('\\', '\\\\').replace('"', '\\"')
            return f'"{quoted}"'
        return str(s)

    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(f"job_id: {job['job_id']}\n")
        f.write(f"title: {yaml_quote(job['title'])}\n")
        f.write(f"company: {yaml_quote(job['company'])}\n")
        f.write(f"location: {yaml_quote(job['location'])}\n")
        if job['work_type']:
            f.write(f"work_type: {yaml_quote(job['work_type'])}\n")
        if job['level']:
            f.write(f"level: {yaml_quote(job['level'])}\n")
        if job['skills']:
            f.write(f"skills:\n")
            for skill in job['skills']:
                f.write(f"  - {yaml_quote(skill)}\n")
        if job['company_size']:
            f.write(f"company_size: {yaml_quote(job['company_size'])}\n")
        if job['compensation']:
            f.write(f"compensation: {yaml_quote(job['compensation'])}\n")
        if job['description']:
            f.write(f"description: |\n")
            for line in job['description'].split('\n'):
                f.write(f"  {line}\n")
        if job['industries']:
            f.write(f"industries:\n")
            for ind in job['industries']:
                f.write(f"  - {yaml_quote(ind)}\n")
        if job['posted_date']:
            f.write(f"posted_date: {yaml_quote(job['posted_date'])}\n")
        f.write(f"url: {yaml_quote(job['url'])}\n")
        f.write(f"source: {yaml_quote(job['source'])}\n")


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
