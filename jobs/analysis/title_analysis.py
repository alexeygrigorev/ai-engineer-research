#!/usr/bin/env python3
"""Analyze job titles - what other names do AI engineers go under?"""
import yaml
from pathlib import Path
from collections import Counter, defaultdict

STRUCTURED_DIR = Path(__file__).parent.parent / "structured"


def load_all_jobs():
    """Load all structured job files."""
    jobs = []
    for file in STRUCTURED_DIR.glob("*.yaml"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                jobs.append(yaml.safe_load(f))
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return jobs


def normalize_title(title):
    """Normalize title for grouping."""
    title = title.lower()
    # Remove common suffixes/prefixes for grouping
    for kw in ['senior', 'staff', 'principal', 'lead', 'junior', 'sr.', 'sr', 'lead', 'iii', 'ii', 'i']:
        title = title.replace(kw, '').strip()
    return title


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    # Group by AI type and analyze titles
    for ai_type in ['ai-first', 'ai-support', 'ml-first']:
        type_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == ai_type]
        print(f"\n{'='*70}")
        print(f"{ai_type.upper()} - Titles ({len(type_jobs)} jobs)")
        print('='*70)

        titles = [j.get('position', {}).get('title', '') for j in type_jobs]
        title_counter = Counter(titles)

        # Top unique titles
        print(f"\n  Top 30 unique titles:")
        for title, count in title_counter.most_common(30):
            print(f"    {title}: {count}")

        # Normalized titles (grouping seniority variants)
        normalized = defaultdict(list)
        for job in type_jobs:
            title = job.get('position', {}).get('title', '')
            norm = normalize_title(title)
            normalized[norm].append(title)

        print(f"\n  Grouped by base title (top 20):")
        sorted_groups = sorted(normalized.items(), key=lambda x: len(x[1]), reverse=True)
        for base, variants in sorted_groups[:20]:
            # Show unique variants
            unique_variants = list(set(variants))[:5]
            print(f"    {base} ({len(variants)}): {unique_variants}")

    # Find titles that are mostly AI-first vs AI-support
    print(f"\n{'='*70}")
    print("TITLE CLUSTERS - Which titles indicate which type?")
    print('='*70)

    # Group by normalized title and track ai_type distribution
    title_ai_types = defaultdict(Counter)
    for job in jobs:
        title = job.get('position', {}).get('title', '')
        norm = normalize_title(title)
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')
        title_ai_types[norm][ai_type] += 1

    # Find clusters
    ai_first_clusters = []
    ai_support_clusters = []
    mixed_clusters = []

    for title, types in title_ai_types.items():
        total = sum(types.values())
        if total < 3:  # Skip very rare titles
            continue

        ai_first_pct = types.get('ai-first', 0) / total * 100
        ai_support_pct = types.get('ai-support', 0) / total * 100

        if ai_first_pct >= 75:
            ai_first_clusters.append((title, total, dict(types)))
        elif ai_support_pct >= 75:
            ai_support_clusters.append((title, total, dict(types)))
        else:
            mixed_clusters.append((title, total, dict(types)))

    print(f"\n  Titles that are STRONGLY AI-FIRST (75%+):")
    for title, total, types in sorted(ai_first_clusters, key=lambda x: x[1], reverse=True)[:20]:
        pct = types.get('ai-first', 0) / total * 100
        print(f"    {title}: {total} jobs ({pct:.0f}% AI-First)")

    print(f"\n  Titles that are STRONGLY AI-SUPPORT (75%+):")
    for title, total, types in sorted(ai_support_clusters, key=lambda x: x[1], reverse=True)[:20]:
        pct = types.get('ai-support', 0) / total * 100
        print(f"    {title}: {total} jobs ({pct:.0f}% AI-Support)")

    print(f"\n  Titles that are MIXED (<75% for either):")
    for title, total, types in sorted(mixed_clusters, key=lambda x: x[1], reverse=True)[:15]:
        ai_first_pct = types.get('ai-first', 0) / total * 100
        ai_support_pct = types.get('ai-support', 0) / total * 100
        print(f"    {title}: {total} jobs ({ai_first_pct:.0f}% AI-First, {ai_support_pct:.0f}% AI-Support)")

    # What words appear in AI-first titles vs AI-support titles?
    print(f"\n{'='*70}")
    print("TITLE KEYWORD ANALYSIS")
    print('='*70)

    ai_first_titles = [j.get('position', {}).get('title', '').lower() for j in jobs
                       if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']
    ai_support_titles = [j.get('position', {}).get('title', '').lower() for j in jobs
                         if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support']

    keywords = ['ai', 'machine learning', 'ml', 'data scientist', 'research', 'applied',
                'engineer', 'developer', 'platform', 'infrastructure', 'product',
                'solutions', 'full-stack', 'backend', 'frontend', 'devops', 'sre',
                'agent', 'llm', 'genai', 'generative', 'model', 'deployment']

    print(f"\n  Keywords in AI-FIRST titles ({len(ai_first_titles)} titles):")
    for kw in keywords:
        count = sum(1 for t in ai_first_titles if kw in t)
        if count > 0:
            pct = count / len(ai_first_titles) * 100
            print(f"    '{kw}': {count} ({pct:.1f}%)")

    print(f"\n  Keywords in AI-SUPPORT titles ({len(ai_support_titles)} titles):")
    for kw in keywords:
        count = sum(1 for t in ai_support_titles if kw in t)
        if count > 0:
            pct = count / len(ai_support_titles) * 100
            print(f"    '{kw}': {count} ({pct:.1f}%)")


if __name__ == '__main__':
    main()
