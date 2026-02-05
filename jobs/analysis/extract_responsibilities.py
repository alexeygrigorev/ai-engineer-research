#!/usr/bin/env python3
"""Extract all responsibilities from structured job data to a file."""
import yaml
from pathlib import Path
from collections import Counter, defaultdict

STRUCTURED_DIR = Path(__file__).parent.parent / "structured"
OUTPUT_FILE = Path(__file__).parent.parent / "all_responsibilities.txt"


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


def extract_all_responsibilities(jobs):
    """Extract and categorize all responsibilities."""
    all_responsibilities = []
    responsibility_sources = []

    for job in jobs:
        company = job.get('company', {}).get('name', 'Unknown')
        title = job.get('position', {}).get('title', 'Unknown')
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')
        responsibilities = job.get('position', {}).get('responsibilities', [])

        if isinstance(responsibilities, list):
            for resp in responsibilities:
                all_responsibilities.append(resp)
                responsibility_sources.append({
                    'responsibility': resp,
                    'company': company,
                    'title': title,
                    'ai_type': ai_type,
                })

    return all_responsibilities, responsibility_sources


def categorize_responsibilities(responsibilities):
    """Categorize responsibilities by keywords."""
    keyword_categories = {
        'Build/Implement Systems': ['build', 'implement', 'develop', 'create', 'construct', 'design system'],
        'Deploy/Production': ['deploy', 'production', 'serve', 'release', 'ship', 'launch'],
        'RAG/Retrieval': ['rag', 'retrieval', 'knowledge base', 'vector', 'semantic search'],
        'Agents/Agentic': ['agent', 'agentic', 'autonomous', 'copilot', 'workflow automation'],
        'Fine-tuning/Training': ['fine-tun', 'finetun', 'train model', 'custom model', 'lora', 'peft'],
        'Prompt Engineering': ['prompt', 'prompting', 'prompt engineer'],
        'Evaluation/Testing': ['evaluat', 'test', 'benchmark', 'quality', 'measure', 'assess'],
        'Data/Pipelines': ['data pipeline', 'etl', 'data engineer', 'preprocess', 'dataset', 'data quality'],
        'Infrastructure/Platform': ['platform', 'infrastructure', 'mlops', 'gpu', 'cluster', 'scalable'],
        'API/Integration': ['api', 'integrate', 'sdk', 'library', 'interface'],
        'Frontend/UI': ['frontend', 'ui', 'ux', 'interface', 'dashboard', 'chatbot', 'web app'],
        'Research/Experiment': ['research', 'experiment', 'novel', 'state of the art', 'sota', 'publish'],
        'Customer/Client Work': ['customer', 'client', 'consult', 'stakeholder', 'user feedback'],
        'Collaboration/Team': ['collaborat', 'team', 'mentor', 'lead', 'guide', 'work with'],
        'Monitor/Maintenance': ['monitor', 'maintain', 'observ', 'incident', 'debug', 'troubleshoot'],
        'Performance/Optimization': ['optim', 'performance', 'latency', 'efficient', 'speed', 'scale'],
        'Security/Safety': ['secur', 'safety', 'protect', 'compliance', 'risk'],
    }

    categorized = defaultdict(list)
    uncategorized = []

    for resp in responsibilities:
        resp_lower = resp.lower()
        matched = False
        for category, keywords in keyword_categories.items():
            if any(kw in resp_lower for kw in keywords):
                categorized[category].append(resp)
                matched = True
                break
        if not matched:
            uncategorized.append(resp)

    return categorized, uncategorized


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    all_responsibilities, resp_sources = extract_all_responsibilities(jobs)

    print(f"Total responsibilities extracted: {len(all_responsibilities)}")

    # Write all responsibilities to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# All Responsibilities from {len(jobs)} Job Descriptions\n\n")
        f.write(f"Total responsibilities: {len(all_responsibilities)}\n\n")
        f.write("=" * 70 + "\n\n")

        for i, resp in enumerate(all_responsibilities, 1):
            f.write(f"{i}. {resp}\n")

    print(f"Written to {OUTPUT_FILE}")

    # Categorize and analyze
    categorized, uncategorized = categorize_responsibilities(all_responsibilities)

    print("\n" + "=" * 70)
    print("RESPONSIBILITY CATEGORIES")
    print("=" * 70)

    for category, resps in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{category}: {len(resps)} mentions")
        # Show unique examples
        unique = list(set(resps))[:5]
        for resp in unique:
            print(f"  - {resp[:80]}...")

    print(f"\n\nUncategorized: {len(uncategorized)}")

    # Analyze by AI type
    print("\n" + "=" * 70)
    print("RESPONSIBILITIES BY AI TYPE")
    print("=" * 70)

    ai_first_resps = [s for s in resp_sources if s['ai_type'] == 'ai-first']
    ai_support_resps = [s for s in resp_sources if s['ai_type'] == 'ai-support']

    print(f"\nAI-First: {len(ai_first_resps)} responsibilities")
    print(f"AI-Support: {len(ai_support_resps)} responsibilities")

    # Most common words
    print("\n" + "=" * 70)
    print("MOST COMMON WORDS IN RESPONSIBILITIES")
    print("=" * 70)

    word_counter = Counter()
    for resp in all_responsibilities:
        words = resp.lower().split()
        for word in words:
            if len(word) > 3:
                word_counter[word] += 1

    # Filter out common words
    common_words = {'with', 'from', 'they', 'have', 'been', 'development',
                    'working', 'including', 'support', 'within', 'will', 'work'}
    for word in common_words:
        word_counter.pop(word, None)

    for word, count in word_counter.most_common(30):
        print(f"  {word}: {count}")


if __name__ == '__main__':
    main()
