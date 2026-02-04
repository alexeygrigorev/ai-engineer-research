#!/usr/bin/env python3
"""Remove duplicates from 250_jobs.md"""
import re
from collections import defaultdict

INPUT_FILE = "report/250_jobs.md"
OUTPUT_FILE = "report/250_jobs_unique.md"

# Parse jobs
job_pattern = r'### (\d+)\.\s+(.+?)\n\n\*\*Company:\*\*\s+(.+?)\n\n\*\*Location:\*\*\s+(.+?)\n\n\*\*Date Posted:\*\*\s+(.+?)\n\n\*\*Source:\*\*\s+(.+?)\n\n\*\*Link:\*\*\s+(.+?)\n\n---'

jobs = []
seen = {}

# First pass: track by link (aggregator pages) and by company+title+location
link_groups = defaultdict(list)
job_key_groups = defaultdict(list)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    content = f.read()

matches = re.findall(job_pattern, content, re.MULTILINE | re.DOTALL)

for match in matches:
    number, title, company, location, date, source, link = match
    title = title.strip()
    company = company.strip()
    location = location.strip()
    link = link.strip()
    source = source.strip()

    # Create key for deduplication (company + title + location)
    # Normalize for comparison
    key = f"{company.lower()}|{title.lower()}|{location.lower()}"

    job = {
        "number": int(number),
        "title": title,
        "company": company,
        "location": location,
        "date": date,
        "source": source,
        "link": link
    }

    # Keep first occurrence of each unique job
    if key not in seen:
        seen[key] = job
    else:
        # Prefer jobs with direct links over aggregator pages
        existing_link = seen[key]["link"]
        if any(x in link.lower() for x in ["jobs.esa.int", "careers.salesforce", "getclera", "jobsinparis"]):
            seen[key] = job
        # Keep wellfound over builtin/indeed (more detailed)
        elif "wellfound.com" in link and "wellfound.com" not in existing_link:
            seen[key] = job

# Get unique jobs
unique_jobs = list(seen.values())
unique_jobs.sort(key=lambda x: x["number"])

print(f"Original jobs: {len(matches)}")
print(f"Unique jobs: {len(unique_jobs)}")
print(f"Removed: {len(matches) - len(unique_jobs)} duplicates")

# Find actual duplicates to report
duplicates = []
for key in seen:
    # Find all originals with this key
    matching = [j for j in matches if f"{j[2].lower()}|{j[1].lower()}|{j[4].strip().lower()}" == key]
    if len(matching) > 1:
        duplicates.append((key, len(matching)))

if duplicates:
    print(f"\nTop duplicate groups:")
    for dup, count in sorted(duplicates, key=lambda x: -x[1])[:10]:
        print(f"  {dup[:60]}... ({count} copies)")

# Write deduplicated file
output = f"""# AI Engineer Job Postings (Deduplicated)

*Source: AI Engineering Job Postings Aggregation*
*Total listings: {len(unique_jobs)} (deduplicated from {len(matches)})*
*Date extracted: February 2026*

---

## Summary

**Total Jobs:** {len(unique_jobs)}

**Unique Companies:** {len(set(j["company"] for j in unique_jobs))}

**Locations:** {len(set(j["location"] for j in unique_jobs))}

"""

# Stats
location_counts = defaultdict(int)
company_counts = defaultdict(int)

for job in unique_jobs:
    location_counts[j["location"]] += 1
    company_counts[j["company"]] += 1

top_locations = sorted(location_counts.items(), key=lambda x: -x[1])[:10]
top_companies = sorted(company_counts.items(), key=lambda x: -x[1])[:15]

output += "**Top Locations:**\n\n"
for loc, count in top_locations:
    output += f"- {loc}: {count} jobs\n"

output += "\n**Top Companies Hiring:**\n\n"
for company, count in top_companies:
    output += f"- {company}: {count} jobs\n"

output += "\n---\n\n## All Job Listings\n\n"

for i, job in enumerate(unique_jobs, 1):
    output += f"""### {i}. {job['title']}

**Company:** {job['company']}

**Location:** {job['location']}

**Date Posted:** {job['date']}

**Source:** {job['source']}

**Link:** {job['link']}

---

"""

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(output)

print(f"\nSaved deduplicated file to: {OUTPUT_FILE}")
