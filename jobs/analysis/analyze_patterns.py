#!/usr/bin/env python3
"""Analyze patterns and skill combinations in job data."""
import os
import yaml
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

SCRIPT_DIR = Path(__file__).parent
STRUCTURED_DIR = SCRIPT_DIR.parent / "structured"


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


def analyze_skill_combinations(jobs, category, min_count=5):
    """Find common skill combinations within a category."""
    combos = Counter()

    for job in jobs:
        skills = job.get('position', {}).get('skills', {}).get(category, [])
        if isinstance(skills, list) and len(skills) >= 2:
            # Get all pairs
            for combo in combinations(sorted(set(skills)), 2):
                combos[combo] += 1

    # Return only combinations above threshold
    return {k: v for k, v in combos.items() if v >= min_count}


def analyze_cross_category_patterns(jobs):
    """Find patterns across skill categories."""
    patterns = defaultdict(Counter)

    for job in jobs:
        skills = job.get('position', {}).get('skills', {})
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')

        # Check if job has skills from both categories
        for cat1, cat2 in combinations([k for k in skills.keys() if skills[k]], 2):
            if skills[cat1] and skills[cat2]:
                patterns[(cat1, cat2)][ai_type] += 1

    return patterns


def analyze_title_vs_reality(jobs):
    """Compare job titles to actual AI type classification."""
    title_keywords = {
        'Backend': ['backend', 'back-end', 'back end'],
        'Full Stack': ['full stack', 'full-stack', 'fullstack'],
        'Platform': ['platform'],
        'Infrastructure': ['infrastructure', 'infra'],
        'Data Engineer': ['data engineer', 'data platform'],
        'DevOps/SRE': ['devops', 'sre', 'site reliability', 'reliability'],
        'Research': ['research', 'scientist'],
        'Product': ['product'],
        'Solutions': ['solutions'],
    }

    results = {}
    for keyword, variants in title_keywords.items():
        ai_types = Counter()
        matching_jobs = []
        for job in jobs:
            title = job.get('position', {}).get('title', '').lower()
            if any(v in title for v in variants):
                ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')
                ai_types[ai_type] += 1
                matching_jobs.append(job.get('position', {}).get('title', ''))

        if matching_jobs:
            total = sum(ai_types.values())
            results[keyword] = {
                'count': total,
                'ai_types': dict(ai_types),
                'ai_first_pct': ai_types.get('ai-first', 0) / total * 100 if total > 0 else 0,
                'sample_titles': list(set(matching_jobs))[:5]
            }

    return results


def analyze_genai_framework_cooccurrence(jobs):
    """Which GenAI frameworks appear together?"""
    frameworks = ['LangChain', 'LangGraph', 'LlamaIndex', 'DSPy', 'Haystack',
                  'Semantic Kernel', 'AutoGen', 'CrewAI', 'Phidata']

    framework_combos = Counter()
    framework_totals = Counter()

    for job in jobs:
        genai_skills = job.get('position', {}).get('skills', {}).get('genai', [])
        job_frameworks = [s for s in genai_skills if s in frameworks]

        for fw in job_frameworks:
            framework_totals[fw] += 1

        if len(job_frameworks) >= 2:
            for combo in combinations(sorted(set(job_frameworks)), 2):
                framework_combos[combo] += 1

    return framework_totals, framework_combos


def analyze_by_company_stage(jobs):
    """Compare skill requirements by company stage."""
    stage_groups = {
        'Early': ['Seed', 'Pre-Seed', 'Angel', 'Seed/Series A'],
        'Growth': ['Series A', 'Series B', 'Series B+', 'Series C', 'Series C+'],
        'Late': ['Series D', 'Series D+', 'Series E', 'Series E+', 'Series F', 'Public'],
    }

    stage_skills = {stage: defaultdict(int) for stage in stage_groups}

    for job in jobs:
        stage = job.get('company', {}).get('stage', '')
        skills = job.get('position', {}).get('skills', {})

        # Map to group
        group = None
        if stage:  # Check stage is not None
            for g, stages in stage_groups.items():
                if any(s in stage for s in stages):
                    group = g
                    break

        if group:
            for category, skill_list in skills.items():
                if isinstance(skill_list, list):
                    for skill in skill_list[:10]:  # Limit per category
                        stage_skills[group][skill] += 1

    return stage_skills


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    # GenAI framework analysis
    print("=" * 60)
    print("GENAI FRAMEWORK ANALYSIS")
    print("=" * 60)
    fw_totals, fw_combos = analyze_genai_framework_cooccurrence(jobs)
    print("\n  Framework frequency:")
    for fw, count in fw_totals.most_common():
        print(f"    {fw}: {count}")

    print("\n  Framework combinations (appearing together):")
    for combo, count in fw_combos.most_common(15):
        print(f"    {' + '.join(combo)}: {count}")

    # Title vs reality
    print("\n" + "=" * 60)
    print("TITLE vs REALITY - Does title predict AI type?")
    print("=" * 60)
    title_analysis = analyze_title_vs_reality(jobs)
    for title_type, data in sorted(title_analysis.items(), key=lambda x: x[1]['ai_first_pct']):
        print(f"\n  {title_type} (n={data['count']}):")
        print(f"    AI-First: {data['ai_first_pct']:.1f}%")
        print(f"    Distribution: {data['ai_types']}")
        print(f"    Sample titles: {data['sample_titles'][:3]}")

    # Cross-category patterns
    print("\n" + "=" * 60)
    print("CROSS-CATEGORY SKILL PATTERNS")
    print("=" * 60)
    cross_patterns = analyze_cross_category_patterns(jobs)

    # Show top patterns
    sorted_patterns = sorted(cross_patterns.items(), key=lambda x: sum(x[1].values()), reverse=True)
    for (cat1, cat2), ai_types in sorted_patterns[:10]:
        total = sum(ai_types.values())
        print(f"\n  {cat1} + {cat2} (n={total}):")
        for ai_type, count in ai_types.most_common():
            print(f"    {ai_type}: {count}")

    # GenAI skill combinations
    print("\n" + "=" * 60)
    print("GENAI SKILL COMBINATIONS")
    print("=" * 60)
    genai_combos = analyze_skill_combinations(jobs, 'genai', min_count=10)
    sorted_combos = sorted(genai_combos.items(), key=lambda x: x[1], reverse=True)
    for combo, count in sorted_combos[:20]:
        print(f"  {' + '.join(combo)}: {count}")

    # By company stage
    print("\n" + "=" * 60)
    print("SKILLS BY COMPANY STAGE")
    print("=" * 60)
    stage_skills = analyze_by_company_stage(jobs)
    for stage, skills in stage_skills.items():
        total = sum(skills.values())
        print(f"\n  {stage} stage (top skills):")
        for skill, count in Counter(skills).most_common(10):
            print(f"    {skill}: {count}")


if __name__ == '__main__':
    main()
