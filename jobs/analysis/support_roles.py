#!/usr/bin/env python3
"""Analyze AI-Support roles - what they do and how they differ from AI-First."""
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


def categorize_support_role(job):
    """Categorize AI-Support roles by what they actually do."""
    title = job.get('position', {}).get('title', '').lower()
    resp = ' '.join(job.get('position', {}).get('responsibilities', []))

    categories = {
        'Platform/Infrastructure': ['platform', 'infrastructure', 'infra', 'mlops', 'kubernetes', 'k8s', 'deployment'],
        'Data/Pipelines': ['data engineer', 'data pipeline', 'etl', 'data platform'],
        'Sales/Solutions': ['sales', 'solutions', 'presales', 'customer success'],
        'Backend/General SWE': ['backend', 'api', 'microservices', 'internal tools'],
        'Frontend/UI': ['frontend', 'ui', 'ux', 'full-stack'],
        'SRE/DevOps': ['sre', 'site reliability', 'devops', 'reliability'],
        'Observability/Monitoring': ['observability', 'monitoring', 'evals', 'testing'],
    }

    for category, keywords in categories.items():
        if any(kw in title or kw in resp for kw in keywords):
            return category
    return 'Other'


def is_research_role(job):
    """Determine if a role is research-focused.

    Research roles are characterized by:
    - Working on novel algorithms, techniques, or approaches
    - Publishing papers or working with research teams
    - Focus on model architecture, training methods, safety techniques
    - Experimental work, not production deployment

    NOT research:
    - Applying existing models (that's Applied AI Engineer)
    - Building infrastructure for AI (that's AI-Support)
    - Product engineering with AI APIs (that's AI Engineer)
    """
    title = job.get('position', {}).get('title', '').lower()
    resp = ' '.join(job.get('position', {}).get('responsibilities', []))
    use_cases = ' '.join(job.get('company', {}).get('use_cases', []))

    research_indicators = [
        'research', 'scientist', 'publication', 'paper', 'novel',
        'algorithm', 'architecture development', 'model architecture',
        'training methods', 'safety research', 'rl research',
        'reinforcement learning', 'world model', 'control theory',
        'experimental', 'push sota', 'state of the art'
    ]

    non_research_indicators = [
        'production', 'deploy', 'shipping', 'product',
        'customer', 'enterprise', 'api integration',
        'fine-tuning existing', 'apply', 'implement'
    ]

    research_score = sum(1 for kw in research_indicators if kw in resp or kw in use_cases or kw in title)
    non_research_score = sum(1 for kw in non_research_indicators if kw in resp or kw in use_cases)

    # Explicit research title keywords
    if any(kw in title for kw in ['research engineer', 'scientist', 'research scientist']):
        return True, 'title'

    # Decision based on content
    if research_score > non_research_score and research_score >= 2:
        return True, 'content'

    return False, 'none'


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    # Analyze AI-Support roles
    ai_support_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support']

    print("=" * 70)
    print("AI-SUPPORT ROLES - What they do")
    print("=" * 70)

    support_categories = defaultdict(list)
    for job in ai_support_jobs:
        cat = categorize_support_role(job)
        support_categories[cat].append(job)

    print(f"\n  Total AI-Support roles: {len(ai_support_jobs)}")
    print(f"\n  By category:")

    for cat, cat_jobs in sorted(support_categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n    {cat}: {len(cat_jobs)} jobs")

        # Sample titles
        titles = [j.get('position', {}).get('title', '') for j in cat_jobs]
        unique_titles = list(set(titles))[:5]
        print(f"      Sample titles: {unique_titles}")

        # Sample responsibilities
        if cat_jobs:
            resp_list = cat_jobs[0].get('position', {}).get('responsibilities', [])
            if resp_list:
                print(f"      Example responsibility: {resp_list[0][:80]}...")

    # Research analysis
    print(f"\n{'=' * 70}")
    print("RESEARCH vs NON-RESEARCH ROLES")
    print("=" * 70)

    research_roles = []
    applied_roles = []

    for job in jobs:
        is_research, reason = is_research_role(job)
        if is_research:
            research_roles.append((job, reason))
        else:
            applied_roles.append(job)

    print(f"\n  Research roles: {len(research_roles)} ({len(research_roles)/len(jobs)*100:.1f}%)")
    print(f"  Applied/Production roles: {len(applied_roles)} ({len(applied_roles)/len(jobs)*100:.1f}%)")

    # Research role breakdown by AI type
    research_by_type = Counter()
    for job, _ in research_roles:
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')
        research_by_type[ai_type] += 1

    print(f"\n  Research roles by AI type:")
    for ai_type, count in research_by_type.most_common():
        print(f"    {ai_type}: {count}")

    # Sample research titles
    print(f"\n  Sample Research Role Titles:")
    research_titles = [j[0].get('position', {}).get('title', '') for j in research_roles]
    for title in list(set(research_titles))[:15]:
        print(f"    - {title}")

    # What makes a role research?
    print(f"\n{'=' * 70}")
    print("DEFINING RESEARCH vs APPLIED")
    print("=" * 70)

    print(f"""
  RESEARCH ROLES work on:
    - Novel algorithms and techniques
    - Model architecture design
    - Training methods and optimization
    - Safety and alignment research
    - Publishing papers, pushing SOTA
    - Experimental work with uncertain outcomes

  Keywords: research, scientist, publication, novel, algorithm,
            architecture, state of the art, experimental

  APPLIED / PRODUCTION ROLES work on:
    - Implementing existing models in production
    - Building applications with AI APIs
    - Deploying and monitoring AI systems
    - Fine-tuning models for specific use cases
    - Customer-facing AI solutions
    - Infrastructure and platforms for AI

  Keywords: production, deploy, customer, enterprise, product,
            API integration, shipping, implementation
    """)

    # Show examples of each
    print(f"\n{'=' * 70}")
    print("EXAMPLES")
    print("=" * 70)

    print(f"\n  RESEARCH ROLE EXAMPLE:")
    for job, _ in research_roles[:3]:
        title = job.get('position', {}).get('title', '')
        company = job.get('company', {}).get('name', '')
        resp = job.get('position', {}).get('responsibilities', [])
        if resp:
            print(f"\n    {company}: {title}")
            print(f"    Responsibilities: {resp[0][:100]}...")
            break

    print(f"\n  APPLIED AI ROLE EXAMPLE:")
    for job in applied_roles[:10]:
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', '')
        if ai_type == 'ai-first':
            title = job.get('position', {}).get('title', '')
            company = job.get('company', {}).get('name', '')
            resp = job.get('position', {}).get('responsibilities', [])
            if resp:
                print(f"\n    {company}: {title}")
                print(f"    Responsibilities: {resp[0][:100]}...")
                break

    print(f"\n  AI-SUPPORT ROLE EXAMPLE:")
    for job in ai_support_jobs[:10]:
        title = job.get('position', {}).get('title', '')
        company = job.get('company', {}).get('name', '')
        resp = job.get('position', {}).get('responsibilities', [])
        if resp:
            print(f"\n    {company}: {title}")
            print(f"    Responsibilities: {resp[0][:100]}...")
            break


if __name__ == '__main__':
    main()
