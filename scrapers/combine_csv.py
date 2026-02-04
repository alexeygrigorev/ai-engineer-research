#!/usr/bin/env python3
"""Combine all Built In job JSON files into a single CSV."""
import json
import csv
from pathlib import Path

# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_DIR = PROJECT_ROOT / "jobs" / "builtin"
OUTPUT_FILE = PROJECT_ROOT / "jobs" / "all_jobs.csv"

# All field names that might appear in the job data
FIELDNAMES = ['title', 'company', 'location', 'work_type', 'level', 'compensation', 'link']

all_jobs = []

# Read only the 5 new JSON files
json_files = [
    "berlin_20260204_145248.json",
    "london_20260204_145503.json",
    "amsterdam_20260204_145525.json",
    "newyork_20260204_150017.json",
    "la_20260204_150318.json"
]

for json_name in json_files:
    json_file = INPUT_DIR / json_name
    if json_file.exists():
        print(f"Reading {json_name}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            all_jobs.extend(jobs)
    else:
        print(f"File not found: {json_name}")

print(f"\nTotal jobs: {len(all_jobs)}")

# Write to CSV
with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()

    for job in all_jobs:
        # Only write the fields we want, in the correct order
        row = {
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'location': job.get('location', ''),
            'work_type': job.get('work_type', ''),
            'level': job.get('level', ''),
            'compensation': job.get('compensation', ''),
            'link': job.get('link', '')
        }
        writer.writerow(row)

print(f"Saved to: {OUTPUT_FILE.absolute()}")
