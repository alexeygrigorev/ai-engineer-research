#!/usr/bin/env python3
"""Analyze fine-tuning requirements and use cases."""
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


def analyze_finetuning(jobs):
    """Analyze fine-tuning requirements."""
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']

    ft_keywords = ['fine-tun', 'finetun', 'fine tun', 'custom model', 'specialized model',
                   'domain-specific', 'adaptation', 'lora', 'qlora', 'peft', 'instruction tuning']

    ft_roles = []
    for job in ai_first_jobs:
        title = job.get('position', {}).get('title', '')
        resp = ' '.join(job.get('position', {}).get('responsibilities', []))
        use_cases = ' '.join(job.get('company', {}).get('use_cases', []))
        skills = job.get('position', {}).get('skills', {})
        genai_skills = [s.lower() for s in skills.get('genai', [])]
        ml_skills = [s.lower() for s in skills.get('ml', [])]

        all_text = f"{title} {resp} {use_cases} {' '.join(genai_skills)} {' '.join(ml_skills)}".lower()

        if any(kw in all_text for kw in ft_keywords):
            ft_roles.append({
                'title': title,
                'company': job.get('company', {}).get('name', ''),
                'responsibilities': job.get('position', {}).get('responsibilities', []),
                'use_cases': job.get('company', {}).get('use_cases', []),
                'skills': skills,
            })

    return ft_roles, len(ai_first_jobs)


def extract_finetuning_use_cases(ft_roles):
    """Extract and categorize fine-tuning use cases."""
    use_case_categories = {
        'Domain knowledge': ['domain', 'industry', 'vertical', 'medical', 'legal', 'finance',
                            'healthcare', 'scientific', 'technical'],
        'Company data': ['company', 'internal', 'proprietary', 'organization', 'proprietary data'],
        'Style/Tone': ['style', 'tone', 'voice', 'brand', 'personality', 'format'],
        'Instruction following': ['instruction', 'task', 'command', 'reasoning', 'agent'],
        'Language': ['language', 'translation', 'multilingual', 'non-english'],
        'Performance': ['faster', 'smaller', 'efficiency', 'latency', 'cost', 'optimize'],
        'Privacy': ['privacy', 'on-premise', 'local', 'offline', 'secure'],
    }

    categorized = defaultdict(list)
    uncategorized = []

    for role in ft_roles:
        for uc in role['use_cases']:
            uc_lower = uc.lower()
            matched = False
            for category, keywords in use_case_categories.items():
                if any(kw in uc_lower for kw in keywords):
                    categorized[category].append(uc)
                    matched = True
                    break
            if not matched and any(kw in uc_lower for kw in ['fine-tun', 'custom', 'specialized']):
                uncategorized.append(uc)

    return categorized, uncategorized


def analyze_finetuning_depth(jobs):
    """Analyze depth of fine-tuning expertise required."""
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']

    deep_ft = []  # Roles where FT is a primary responsibility
    light_ft = []  # Roles where FT is mentioned but not primary
    no_ft = []  # No mention of FT

    for job in ai_first_jobs:
        title = job.get('position', {}).get('title', '')
        resp = ' '.join(job.get('position', {}).get('responsibilities', []))
        use_cases = ' '.join(job.get('company', {}).get('use_cases', []))
        all_text = f"{title} {resp} {use_cases}".lower()

        ft_indicators = ['fine-tun', 'finetun', 'lora', 'qlora', 'peft', 'instruction tuning']
        has_ft = any(kw in all_text for kw in ft_indicators)

        # Check if FT is primary vs secondary
        primary_ft = any([
            'fine-tune' in title.lower(),
            'finetune' in title.lower(),
            resp.count('fine-tun') + resp.count('finetun') >= 2,  # Mentioned multiple times
            'lora' in all_text or 'qlora' in all_text or 'peft' in all_text,  # Specific techniques
        ])

        if has_ft and primary_ft:
            deep_ft.append(job)
        elif has_ft:
            light_ft.append(job)
        else:
            no_ft.append(job)

    return deep_ft, light_ft, no_ft


def main():
    jobs = load_all_jobs()
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']
    print(f"Loaded {len(jobs)} jobs ({len(ai_first_jobs)} AI-First)\n")

    # Fine-tuning prevalence
    print("=" * 70)
    print("HOW MANY AI ENGINEER ROLES REQUIRE FINE-TUNING?")
    print("=" * 70)

    ft_roles, total_ai_first = analyze_finetuning(jobs)

    print(f"\n  AI-First roles mentioning fine-tuning: {len(ft_roles)}/{total_ai_first} ({len(ft_roles)/total_ai_first*100:.1f}%)")

    # Depth analysis
    deep_ft, light_ft, no_ft = analyze_finetuning_depth(jobs)

    print(f"\n  By depth of FT requirement:")
    print(f"    Primary FT responsibility: {len(deep_ft)}/{total_ai_first} ({len(deep_ft)/total_ai_first*100:.1f}%)")
    print(f"    Secondary/occasional FT: {len(light_ft)}/{total_ai_first} ({len(light_ft)/total_ai_first*100:.1f}%)")
    print(f"    No FT mentioned: {len(no_ft)}/{total_ai_first} ({len(no_ft)/total_ai_first*100:.1f}%)")

    # Use cases
    print(f"\n{'=' * 70}")
    print("FINE-TUNING USE CASES")
    print("=" * 70)

    categorized, uncategorized = extract_finetuning_use_cases(ft_roles)

    print(f"\n  Categorized use cases:")
    for category, ucs in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n    {category}: {len(ucs)} mentions")
        # Show unique examples
        unique = list(set(ucs))[:3]
        for uc in unique:
            print(f"      - {uc[:80]}...")

    print(f"\n  Other FT mentions (first 10):")
    for uc in uncategorized[:10]:
        print(f"    - {uc[:80]}...")

    # Sample roles
    print(f"\n{'=' * 70}")
    print("SAMPLE ROLE DESCRIPTIONS")
    print("=" * 70)

    # Deep FT roles
    print(f"\n  PRIMARY FINE-TUNING ROLES:")
    for job in deep_ft[:5]:
        title = job.get('position', {}).get('title', '')
        company = job.get('company', {}).get('name', '')
        resp = job.get('position', {}).get('responsibilities', [])
        print(f"\n    {company}: {title}")
        if resp:
            print(f"      {resp[0][:100]}...")

    # Light FT roles
    print(f"\n  LIGHT FINE-TUNING ROLES:")
    for job in light_ft[:5]:
        title = job.get('position', {}).get('title', '')
        company = job.get('company', {}).get('name', '')
        resp = job.get('position', {}).get('responsibilities', [])
        print(f"\n    {company}: {title}")
        if resp:
            print(f"      {resp[0][:100]}...")


if __name__ == '__main__':
    main()
