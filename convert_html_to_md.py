#!/usr/bin/env python3
"""
Comprehensive HTML to Markdown converter for Grok search result pages.
Extracts ALL content including main text, sources, references, and sidebar links.
"""

from bs4 import BeautifulSoup
from pathlib import Path
import re
from html2text import HTML2Text

def extract_all_links(soup):
    """Extract all external links from the document."""
    all_links = []
    seen_urls = set()

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()

        # Skip internal links
        if href.startswith('#') or href.startswith('javascript:'):
            continue

        # Skip empty or common UI links
        if not href or href in ['/', '?', 'javascript:void(0)']:
            continue

        # Clean the URL
        if href.startswith('?') or href.startswith('&'):
            continue

        # Get link text
        text = a.get_text(strip=True)

        # Skip UI elements
        ui_terms = ['chat', 'search', 'ctrl+k', 'ctrl+j', 'share', 'copy',
                    'close', 'menu', 'more', 'expand', 'collapse']
        if text.lower() in ui_terms:
            continue

        # Deduplicate by URL
        if href not in seen_urls:
            seen_urls.add(href)
            all_links.append({
                'url': href,
                'text': text if text else href
            })

    return all_links


def categorize_links(links):
    """Categorize links by type for better organization."""
    categories = {
        'Reddit': [],
        'LinkedIn': [],
        'YouTube': [],
        'Medium': [],
        'X/Twitter': [],
        'Other': []
    }

    for link in links:
        url = link['url'].lower()
        text = link['text']
        url_full = link['url']

        if 'reddit.com' in url:
            categories['Reddit'].append((text, url_full))
        elif 'linkedin.com' in url:
            categories['LinkedIn'].append((text, url_full))
        elif 'youtube.com' in url or 'youtu.be' in url:
            categories['YouTube'].append((text, url_full))
        elif 'medium.com' in url:
            categories['Medium'].append((text, url_full))
        elif 'x.com' in url or 'twitter.com' in url:
            categories['X/Twitter'].append((text, url_full))
        else:
            categories['Other'].append((text, url_full))

    return categories


def convert_html_to_markdown(html_path, md_path):
    """Convert HTML file to comprehensive Markdown."""
    print(f"Converting: {html_path.name}")

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Remove scripts, styles, and other non-content elements
    for tag in soup.find_all(['script', 'style', 'noscript', 'meta', 'link']):
        tag.decompose()

    # Configure html2text
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_emphasis = False
    h.body_width = 0
    h.unicode_snob = True
    h.skip_internal_links = False
    h.inline_links = True
    h.protect_links = True
    h.mark_code = True
    h.wrap_links = False
    h.single_line_break = False

    # Find main content
    main_content = soup.find('main')
    if not main_content:
        main_content = soup.body if soup.body else soup

    # Convert to markdown
    markdown_content = h.handle(str(main_content))

    # Clean up markdown
    lines = markdown_content.split('\n')
    cleaned_lines = []

    skip_patterns = [
        r'^Ctrl\+[KJ]$',
        r'^Search$',
        r'^Chat$',
        r'^Share$',
        r'^Copy$',
        r'^\s*$',
    ]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue

        # Skip UI noise
        skip = False
        for pattern in skip_patterns:
            if re.match(pattern, stripped):
                skip = True
                break

        if not skip:
            cleaned_lines.append(stripped)

    # Build final markdown
    title = html_path.stem.replace('.html', '').replace('-', ' ')
    final_md = f"# {title}\n\n"
    final_md += '\n'.join(cleaned_lines)

    # Extract and categorize all links
    all_links = extract_all_links(soup)
    categories = categorize_links(all_links)

    # Add comprehensive sources section
    final_md += "\n\n---\n\n"
    final_md += f"## Sources and References ({len(all_links)} links)\n\n"

    for category, links in categories.items():
        if links:
            final_md += f"### {category}\n\n"
            for text, url in links:
                if text and text != url:
                    final_md += f"- [{text}]({url})\n"
                else:
                    final_md += f"- [{url}]({url})\n"
            final_md += "\n"

    # Add raw URL list for reference
    final_md += "### All URLs (Raw List)\n\n"
    for link in all_links:
        final_md += f"- {link['url']}\n"

    # Write markdown file
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(final_md)

    print(f"  -> {md_path.name}: {len(final_md):,} chars, {len(all_links)} links")

    return len(final_md), len(all_links)


def main():
    """Main conversion function."""
    html_dir = Path('C:/Users/alexe/git/ai-engineer-research/research_html')
    report_dir = Path('C:/Users/alexe/git/ai-engineer-research/report')
    report_dir.mkdir(exist_ok=True)

    files = [
        ('Recent AI Engineering Interview Experiences 2025-2026 - Grok.html',
         'Recent_AI_Engineering_Interview_Experiences_Grok.md'),
        ('Recent AI Engineering Interview Experiences 2025-2026 - links.html',
         'Recent_AI_Engineering_Interview_Experiences_Links.md'),
        ('Recent AI Engineering Interview Experiences 2025-2026 - links2.html',
         'Recent_AI_Engineering_Interview_Experiences_Links2.md'),
        ('Recent AI Engineering Interview Experiences 2025-2026 - links 3.html',
         'Recent_AI_Engineering_Interview_Experiences_Links3.md'),
    ]

    print("=" * 60)
    print("HTML to Markdown Conversion - Grok Research Pages")
    print("=" * 60)

    total_chars = 0
    total_links = 0

    for html_file, md_file in files:
        html_path = html_dir / html_file
        md_path = report_dir / md_file

        if html_path.exists():
            chars, links = convert_html_to_markdown(html_path, md_path)
            total_chars += chars
            total_links += links
        else:
            print(f"  ERROR: {html_path} not found!")

    print("\n" + "=" * 60)
    print(f"Conversion complete!")
    print(f"Total files processed: {len(files)}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total unique links across all files: {total_links}")
    print("=" * 60)


if __name__ == '__main__':
    main()
