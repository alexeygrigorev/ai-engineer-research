#!/usr/bin/env python3
"""Analyze structured job data."""
import os
import yaml
from pathlib import Path
from collections import Counter, defaultdict

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


def analyze_ai_types(jobs):
    """Analyze AI type distribution."""
    ai_types = Counter()
    for job in jobs:
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')
        ai_types[ai_type] += 1
    return ai_types


def analyze_companies(jobs):
    """Analyze company distribution."""
    companies = Counter()
    stages = Counter()
    for job in jobs:
        company = job.get('company', {}).get('name', 'Unknown')
        companies[company] += 1
        stage = job.get('company', {}).get('stage')
        if stage:
            stages[stage] += 1
    return companies, stages


def analyze_skills(jobs):
    """Analyze skill distribution by category."""
    category_skills = defaultdict(Counter)
    skill_totals = Counter()

    for job in jobs:
        skills = job.get('position', {}).get('skills', {})
        for category, skill_list in skills.items():
            if isinstance(skill_list, list):
                for skill in skill_list:
                    category_skills[category][skill] += 1
                    skill_totals[(category, skill)] += 1

    return category_skills, skill_totals


def analyze_roles(jobs):
    """Analyze role patterns."""
    customer_facing = 0
    management = 0
    titles = Counter()

    for job in jobs:
        position = job.get('position', {})
        if position.get('is_customer_facing'):
            customer_facing += 1
        if position.get('is_management'):
            management += 1
        titles[position.get('title', 'Unknown')] += 1

    return customer_facing, management, titles


def analyze_use_cases(jobs):
    """Extract common use case patterns."""
    all_use_cases = []
    for job in jobs:
        use_cases = job.get('company', {}).get('use_cases', [])
        if isinstance(use_cases, list):
            all_use_cases.extend(use_cases)

    # Simple keyword analysis
    keywords = Counter()
    keyword_categories = {
        'RAG': ['rag', 'retrieval'],
        'Agents': ['agent', 'agentic', 'autonomous'],
        'Fine-tuning': ['fine-tun', 'finetun', 'custom', 'specialized'],
        'Enterprise': ['enterprise', 'business'],
        'Customer-facing': ['customer', 'client'],
        'Evaluation': ['evaluat', 'quality', 'testing'],
        'Inference': ['inference', 'serving', 'deployment'],
        'Search': ['search', 'semantic'],
    }

    for uc in all_use_cases:
        uc_lower = uc.lower()
        for category, keywords_list in keyword_categories.items():
            if any(kw in uc_lower for kw in keywords_list):
                keywords[category] += 1

    return keywords, len(all_use_cases)


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    # AI Type distribution
    print("=" * 60)
    print("AI TYPE DISTRIBUTION")
    print("=" * 60)
    ai_types = analyze_ai_types(jobs)
    total = sum(ai_types.values())
    for ai_type, count in ai_types.most_common():
        pct = count / total * 100
        print(f"  {ai_type}: {count} ({pct:.1f}%)")
    print()

    # Company analysis
    print("=" * 60)
    print("COMPANY ANALYSIS")
    print("=" * 60)
    companies, stages = analyze_companies(jobs)
    print(f"  Unique companies: {len(companies)}")
    print(f"\n  Top 20 companies by job count:")
    for company, count in companies.most_common(20):
        print(f"    {company}: {count}")

    print(f"\n  Company stages:")
    for stage, count in stages.most_common():
        print(f"    {stage}: {count}")
    print()

    # Role analysis
    print("=" * 60)
    print("ROLE ANALYSIS")
    print("=" * 60)
    customer_facing, management, titles = analyze_roles(jobs)
    print(f"  Customer-facing roles: {customer_facing} ({customer_facing/len(jobs)*100:.1f}%)")
    print(f"  Management roles: {management} ({management/len(jobs)*100:.1f}%)")
    print(f"\n  Top 15 most common titles:")
    for title, count in titles.most_common(15):
        print(f"    {title}: {count}")
    print()

    # Skills analysis
    print("=" * 60)
    print("SKILLS ANALYSIS - Top 10 per category")
    print("=" * 60)
    category_skills, skill_totals = analyze_skills(jobs)
    for category in ['genai', 'ml', 'web', 'databases', 'data', 'cloud', 'ops', 'languages']:
        if category in category_skills:
            print(f"\n  {category.upper()}:")
            for skill, count in category_skills[category].most_common(10):
                print(f"    {skill}: {count}")
    print()

    # Use cases analysis
    print("=" * 60)
    print("USE CASE PATTERNS")
    print("=" * 60)
    use_case_keywords, total_use_cases = analyze_use_cases(jobs)
    print(f"  Total use cases extracted: {total_use_cases}")
    print(f"\n  Most common patterns:")
    for pattern, count in use_case_keywords.most_common():
        print(f"    {pattern}: {count}")
    print()

    # Find interesting examples
    print("=" * 60)
    print("INTERESTING FINDINGS")
    print("=" * 60)

    # AI-support roles that are customer-facing
    ai_support_customer_facing = [
        j for j in jobs
        if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support'
        and j.get('position', {}).get('is_customer_facing')
    ]
    print(f"\n  AI-Support roles that are customer-facing: {len(ai_support_customer_facing)}")
    for j in ai_support_customer_facing[:5]:
        print(f"    - {j.get('company', {}).get('name')}: {j.get('position', {}).get('title')}")

    # AI-first roles with minimal genai skills
    ai_first_low_genai = [
        j for j in jobs
        if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first'
        and len(j.get('position', {}).get('skills', {}).get('genai', [])) <= 1
    ]
    print(f"\n  AI-First roles with minimal GenAI skills: {len(ai_first_low_genai)}")
    for j in ai_first_low_genai[:5]:
        skills = j.get('position', {}).get('skills', {}).get('genai', [])
        print(f"    - {j.get('company', {}).get('name')}: {skills}")

    # Titles with "AI Engineer" that are actually ai-support
    ai_engineer_support = [
        j for j in jobs
        if 'ai engineer' in j.get('position', {}).get('title', '').lower()
        and j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support'
    ]
    print(f"\n  'AI Engineer' titles that are AI-Support: {len(ai_engineer_support)}")
    for j in ai_engineer_support[:5]:
        print(f"    - {j.get('company', {}).get('name')}: {j.get('position', {}).get('title')}")

    # FDE roles
    fde_roles = [
        j for j in jobs
        if 'forward' in j.get('position', {}).get('title', '').lower()
        or 'deployed' in j.get('position', {}).get('title', '').lower()
    ]
    print(f"\n  Forward Deployed Engineer roles: {len(fde_roles)}")
    fde_ai_first = [j for j in fde_roles if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']
    print(f"    Classified as AI-First: {len(fde_ai_first)}")

    # ML-first roles
    ml_first = [
        j for j in jobs
        if j.get('position', {}).get('ai_type', {}).get('type') == 'ml-first'
    ]
    print(f"\n  ML-First roles: {len(ml_first)}")
    for j in ml_first[:10]:
        print(f"    - {j.get('company', {}).get('name')}: {j.get('position', {}).get('title')}")


if __name__ == '__main__':
    main()
