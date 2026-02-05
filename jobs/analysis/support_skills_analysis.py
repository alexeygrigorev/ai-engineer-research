#!/usr/bin/env python3
"""Analyze AI-Support roles - what AI knowledge do they need?"""
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


def compare_skills_by_type(jobs):
    """Compare skills between AI-First and AI-Support roles."""
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']
    ai_support_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support']

    # Count skills by type
    def count_roles_with_skill(jobs, skill_name):
        count = 0
        for job in jobs:
            skills = job.get('position', {}).get('skills', {})
            all_skills = []
            for cat, skill_list in skills.items():
                if isinstance(skill_list, list):
                    all_skills.extend([s.lower() for s in skill_list])
            if any(skill_name.lower() in s for s in all_skills):
                count += 1
        return count

    # Key skills to check
    key_skills = {
        'genai': ['RAG', 'prompt engineering', 'agents', 'LangChain', 'LLMs'],
        'ml': ['PyTorch', 'TensorFlow', 'fine-tuning', 'machine learning'],
        'web': ['React', 'FastAPI', 'TypeScript', 'APIs'],
        'ops': ['Docker', 'Kubernetes', 'CI/CD'],
        'cloud': ['AWS', 'Azure', 'GCP'],
    }

    comparison = {}
    for category, skills in key_skills.items():
        comparison[category] = {}
        for skill in skills:
            ai_first_count = count_roles_with_skill(ai_first_jobs, skill)
            ai_support_count = count_roles_with_skill(ai_support_jobs, skill)
            comparison[category][skill] = {
                'ai_first': ai_first_count,
                'ai_support': ai_support_count,
                'ai_first_pct': ai_first_count / len(ai_first_jobs) * 100 if ai_first_jobs else 0,
                'ai_support_pct': ai_support_count / len(ai_support_jobs) * 100 if ai_support_jobs else 0,
            }

    return comparison, len(ai_first_jobs), len(ai_support_jobs)


def analyze_support_ai_knowledge(jobs):
    """What AI knowledge do support roles actually need?"""
    ai_support_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support']

    # Find support roles with GenAI skills
    support_with_genai = []
    support_without_genai = []

    for job in ai_support_jobs:
        genai_skills = job.get('position', {}).get('skills', {}).get('genai', [])
        if genai_skills:
            support_with_genai.append({
                'title': job.get('position', {}).get('title', ''),
                'company': job.get('company', {}).get('name', ''),
                'genai_skills': genai_skills,
                'all_skills': job.get('position', {}).get('skills', {}),
            })
        else:
            support_without_genai.append({
                'title': job.get('position', {}).get('title', ''),
                'company': job.get('company', {}).get('name', ''),
                'all_skills': job.get('position', {}).get('skills', {}),
            })

    return support_with_genai, support_without_genai


def analyze_support_entry_level(jobs):
    """Are support roles more entry-level friendly?"""
    # Check for entry-level indicators in titles
    entry_keywords = ['junior', 'entry', 'associate', 'grad', 'intern', 'beginner']

    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']
    ai_support_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-support']

    ai_first_entry = [j for j in ai_first_jobs if any(kw in j.get('position', {}).get('title', '').lower() for kw in entry_keywords)]
    ai_support_entry = [j for j in ai_support_jobs if any(kw in j.get('position', {}).get('title', '').lower() for kw in entry_keywords)]

    return len(ai_first_entry), len(ai_support_entry), len(ai_first_jobs), len(ai_support_jobs)


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    # Compare skills
    print("=" * 70)
    print("AI-FIRST VS AI-SUPPORT: SKILL COMPARISON")
    print("=" * 70)

    comparison, n_ai_first, n_ai_support = compare_skills_by_type(jobs)

    print(f"\n  AI-First: {n_ai_first} jobs")
    print(f"  AI-Support: {n_ai_support} jobs\n")

    for category, skills in comparison.items():
        print(f"\n  {category.upper()}:")
        for skill, counts in skills.items():
            print(f"    {skill:20s} | AI-First: {counts['ai_first']:3d} ({counts['ai_first_pct']:5.1f}%) | AI-Support: {counts['ai_support']:3d} ({counts['ai_support_pct']:5.1f}%)")

    # Support AI knowledge
    print(f"\n{'=' * 70}")
    print("DO AI-SUPPORT ROLES NEED GENAI KNOWLEDGE?")
    print("=" * 70)

    support_with_genai, support_without_genai = analyze_support_ai_knowledge(jobs)

    print(f"\n  AI-Support roles WITH GenAI skills: {len(support_with_genai)}/{n_ai_support} ({len(support_with_genai)/n_ai_support*100:.1f}%)")
    print(f"  AI-Support roles WITHOUT GenAI skills: {len(support_without_genai)}/{n_ai_support} ({len(support_without_genai)/n_ai_support*100:.1f}%)")

    print(f"\n  Most common GenAI skills in AI-Support roles:")
    all_genai = []
    for job in support_with_genai:
        all_genai.extend(job['genai_skills'])
    genai_counter = Counter(all_genai)
    for skill, count in genai_counter.most_common(15):
        pct = count / n_ai_support * 100
        print(f"    {skill}: {count} ({pct:.1f}%)")

    # Sample support roles with/without GenAI
    print(f"\n{'=' * 70}")
    print("SAMPLE AI-SUPPORT ROLES")
    print("=" * 70)

    print(f"\n  WITH GenAI skills (understanding AI but not building it):")
    for job in support_with_genai[:5]:
        print(f"\n    {job['company']}: {job['title']}")
        print(f"      GenAI: {job['genai_skills']}")

    print(f"\n  WITHOUT GenAI skills (pure support/infra):")
    for job in support_without_genai[:5]:
        print(f"\n    {job['company']}: {job['title']}")
        all_skills = []
        for cat, skills in job['all_skills'].items():
            if isinstance(skills, list) and skills:
                all_skills.extend(skills[:3])
        print(f"      Skills: {all_skills[:5]}")

    # Entry level analysis
    print(f"\n{'=' * 70}")
    print("ENTRY-LEVEL FRIENDLINESS")
    print("=" * 70)

    ai_first_entry, ai_support_entry, n_ai_first, n_ai_support = analyze_support_entry_level(jobs)

    print(f"\n  AI-First entry-level roles: {ai_first_entry}/{n_ai_first} ({ai_first_entry/n_ai_first*100:.1f}%)")
    print(f"  AI-Support entry-level roles: {ai_support_entry}/{n_ai_support} ({ai_support_entry/n_ai_support*100:.1f}%)")


if __name__ == '__main__':
    main()
