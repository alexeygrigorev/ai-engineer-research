#!/usr/bin/env python3
"""Analyze ML knowledge and non-GenAI skills for AI Engineers."""
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


def analyze_ml_knowledge(jobs):
    """How much ML do AI-First engineers need to know?"""
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']

    ml_skills = ['PyTorch', 'TensorFlow', 'Keras', 'JAX', 'scikit-learn', 'XGBoost',
                 'LightGBM', 'fine-tuning', 'model training', 'model evaluation',
                 'embeddings', 'deep learning', 'machine learning', 'neural networks',
                 'optimization', 'CUDA', 'transformers', 'huggingface']

    ml_skill_counts = Counter()
    jobs_with_ml = 0
    jobs_with_any_ml = []

    for job in ai_first_jobs:
        skills = job.get('position', {}).get('skills', {})
        all_skills = []
        for cat, skill_list in skills.items():
            if isinstance(skill_list, list):
                all_skills.extend([s.lower() for s in skill_list])

        # Check for ML skills
        job_ml_skills = [s for s in all_skills if any(ml.lower() in s for ml in ml_skills)]
        if job_ml_skills:
            jobs_with_ml += 1
            jobs_with_any_ml.append({
                'title': job.get('position', {}).get('title', ''),
                'company': job.get('company', {}).get('name', ''),
                'ml_skills': job_ml_skills,
                'genai_skills': skills.get('genai', []),
                'other_skills': {k: v for k, v in skills.items() if k != 'genai' and k != 'ml'}
            })

        for ml_skill in ml_skills:
            if any(ml_skill.lower() in s for s in all_skills):
                ml_skill_counts[ml_skill] += 1

    return ml_skill_counts, jobs_with_ml, jobs_with_any_ml, len(ai_first_jobs)


def analyze_non_genai_skills(jobs):
    """What non-GenAI skills do AI engineers need?"""
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']

    # Group skills by category (excluding genai)
    category_skill_counts = defaultdict(Counter)

    for job in ai_first_jobs:
        skills = job.get('position', {}).get('skills', {})
        for category, skill_list in skills.items():
            if category == 'genai':
                continue
            if isinstance(skill_list, list):
                for skill in skill_list:
                    category_skill_counts[category][skill] += 1

    return category_skill_counts, len(ai_first_jobs)


def analyze_full_stack_overlap(jobs):
    """How many AI engineers do full-stack work?"""
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']

    full_stack_indicators = ['react', 'vue', 'next.js', 'frontend', 'typescript', 'javascript',
                             'fastapi', 'flask', 'django', 'api', 'graphql']

    full_stack_count = 0
    frontend_count = 0
    backend_count = 0

    for job in ai_first_jobs:
        skills = job.get('position', {}).get('skills', {})
        all_skills = []
        for cat, skill_list in skills.items():
            if isinstance(skill_list, list):
                all_skills.extend([s.lower() for s in skill_list])

        has_frontend = any(ind in s for s in all_skills for ind in ['react', 'vue', 'next.js', 'frontend', 'typescript', 'javascript'])
        has_backend = any(ind in s for s in all_skills for ind in ['fastapi', 'flask', 'django', 'api', 'graphql', 'rest'])

        if has_frontend and has_backend:
            full_stack_count += 1
        if has_frontend:
            frontend_count += 1
        if has_backend:
            backend_count += 1

    return full_stack_count, frontend_count, backend_count, len(ai_first_jobs)


def main():
    jobs = load_all_jobs()
    ai_first_jobs = [j for j in jobs if j.get('position', {}).get('ai_type', {}).get('type') == 'ai-first']
    print(f"Loaded {len(jobs)} jobs ({len(ai_first_jobs)} AI-First)\n")

    # ML Knowledge Analysis
    print("=" * 70)
    print("HOW MUCH ML DO AI ENGINEERS NEED TO KNOW?")
    print("=" * 70)

    ml_skill_counts, jobs_with_ml, jobs_with_any_ml, total_ai_first = analyze_ml_knowledge(jobs)

    print(f"\n  AI-First jobs requiring ML skills: {jobs_with_ml}/{total_ai_first} ({jobs_with_ml/total_ai_first*100:.1f}%)")
    print(f"\n  Most common ML skills in AI-First roles:")

    for skill, count in ml_skill_counts.most_common(15):
        pct = count / total_ai_first * 100
        print(f"    {skill}: {count} ({pct:.1f}%)")

    # Examples of roles with ML vs without
    print(f"\n  Examples:")
    ml_heavy = sorted(jobs_with_any_ml, key=lambda x: len(x['ml_skills']), reverse=True)[:3]
    for job in ml_heavy:
        print(f"\n    {job['company']}: {job['title']}")
        print(f"      ML skills: {job['ml_skills'][:5]}")

    ml_light = [j for j in jobs_with_any_ml if len(j['ml_skills']) <= 2][:3]
    for job in ml_light:
        print(f"\n    {job['company']}: {job['title']}")
        print(f"      ML skills: {job['ml_skills']}")

    # Non-GenAI Skills Analysis
    print(f"\n{'=' * 70}")
    print("WHAT NON-GENAI SKILLS DO AI ENGINEERS NEED?")
    print("=" * 70)

    category_skills, total = analyze_non_genai_skills(jobs)

    print(f"\n  By category (percentage of AI-First jobs):")
    for category in ['web', 'cloud', 'ops', 'languages', 'databases', 'data']:
        if category in category_skills:
            print(f"\n    {category.upper()}:")
            for skill, count in category_skills[category].most_common(8):
                pct = count / total * 100
                print(f"      {skill}: {count} ({pct:.1f}%)")

    # Full-stack analysis
    print(f"\n{'=' * 70}")
    print("FULL-STACK EXPECTATIONS")
    print("=" * 70)

    fs_count, fe_count, be_count, total = analyze_full_stack_overlap(jobs)

    print(f"\n  AI-First jobs with frontend skills: {fe_count}/{total} ({fe_count/total*100:.1f}%)")
    print(f"  AI-First jobs with backend skills: {be_count}/{total} ({be_count/total*100:.1f}%)")
    print(f"  AI-First jobs with BOTH (full-stack): {fs_count}/{total} ({fs_count/total*100:.1f}%)")

    # What percentage do ONLY GenAI vs GenAI + other stuff?
    print(f"\n{'=' * 70}")
    print("PURE GENAI VS GENAI + OTHER SKILLS")
    print("=" * 70)

    only_genai = 0
    genai_plus_other = 0
    genai_plus_ml = 0
    genai_plus_web = 0
    genai_plus_ops = 0

    for job in ai_first_jobs:
        skills = job.get('position', {}).get('skills', {})
        genai = len(skills.get('genai', []))
        ml = len(skills.get('ml', []))
        web = len(skills.get('web', []))
        ops = len(skills.get('ops', []))
        other = ml + web + ops + len(skills.get('cloud', [])) + len(skills.get('data', [])) + len(skills.get('databases', []))

        if genai > 0 and other == 0:
            only_genai += 1
        if genai > 0 and other > 0:
            genai_plus_other += 1
        if genai > 0 and ml > 0:
            genai_plus_ml += 1
        if genai > 0 and web > 0:
            genai_plus_web += 1
        if genai > 0 and ops > 0:
            genai_plus_ops += 1

    print(f"\n  Pure GenAI (no other tech skills): {only_genai}/{total} ({only_genai/total*100:.1f}%)")
    print(f"  GenAI + ML skills: {genai_plus_ml}/{total} ({genai_plus_ml/total*100:.1f}%)")
    print(f"  GenAI + Web skills: {genai_plus_web}/{total} ({genai_plus_web/total*100:.1f}%)")
    print(f"  GenAI + Ops skills: {genai_plus_ops}/{total} ({genai_plus_ops/total*100:.1f}%)")
    print(f"  GenAI + ANY other skills: {genai_plus_other}/{total} ({genai_plus_other/total*100:.1f}%)")


if __name__ == '__main__':
    main()
