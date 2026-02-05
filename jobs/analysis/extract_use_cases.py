#!/usr/bin/env python3
"""Extract all use cases from structured job data to a file."""
import yaml
from pathlib import Path
from collections import Counter, defaultdict

STRUCTURED_DIR = Path(__file__).parent.parent / "structured"
OUTPUT_FILE = Path(__file__).parent.parent / "all_use_cases.txt"


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


def extract_all_use_cases(jobs):
    """Extract and categorize all use cases."""
    all_use_cases = []
    use_case_sources = []

    for job in jobs:
        company = job.get('company', {}).get('name', 'Unknown')
        title = job.get('position', {}).get('title', 'Unknown')
        ai_type = job.get('position', {}).get('ai_type', {}).get('type', 'unknown')
        use_cases = job.get('company', {}).get('use_cases', [])

        if isinstance(use_cases, list):
            for uc in use_cases:
                all_use_cases.append(uc)
                use_case_sources.append({
                    'use_case': uc,
                    'company': company,
                    'title': title,
                    'ai_type': ai_type,
                })

    return all_use_cases, use_case_sources


def categorize_use_cases(use_cases):
    """Categorize use cases by keywords."""
    keyword_categories = {
        'Agents / Agentic AI': ['agent', 'agentic', 'autonomous', 'copilot', 'assistant'],
        'Enterprise deployments': ['enterprise', 'business', 'organization', 'company-wide'],
        'Fine-tuning / Custom models': ['fine-tun', 'finetun', 'custom model', 'specialized', 'domain-specific'],
        'Customer-facing solutions': ['customer', 'client', 'user-facing', 'customer service'],
        'RAG / Retrieval': ['rag', 'retrieval', 'knowledge base', 'document'],
        'Inference / Serving': ['inference', 'serving', 'deployment', 'production'],
        'Evaluation / Testing': ['evaluat', 'quality', 'testing', 'benchmark', 'safety'],
        'Search / Semantic search': ['search', 'semantic', 'vector'],
        'Chat / Conversational': ['chat', 'conversational', 'dialog', 'messaging'],
        'Code generation': ['code generation', 'code assistant', 'copilot', 'developer'],
        'Data analysis': ['data analysis', 'analytics', 'insight', 'reporting'],
        'Content creation': ['content', 'writing', 'copy', 'marketing'],
        'Recommendations': ['recommend', 'personalization', 'suggest'],
        'Document processing': ['document', 'pdf', 'extract', 'summarize'],
    }

    categorized = defaultdict(list)
    uncategorized = []

    for uc in use_cases:
        uc_lower = uc.lower()
        matched = False
        for category, keywords in keyword_categories.items():
            if any(kw in uc_lower for kw in keywords):
                categorized[category].append(uc)
                matched = True
                break
        if not matched:
            uncategorized.append(uc)

    return categorized, uncategorized


def main():
    jobs = load_all_jobs()
    print(f"Loaded {len(jobs)} jobs\n")

    all_use_cases, use_case_sources = extract_all_use_cases(jobs)

    print(f"Total use cases extracted: {len(all_use_cases)}")

    # Write all use cases to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# All Use Cases from {len(jobs)} Job Descriptions\n\n")
        f.write(f"Total use cases: {len(all_use_cases)}\n\n")
        f.write("=" * 70 + "\n\n")

        for i, uc in enumerate(all_use_cases, 1):
            f.write(f"{i}. {uc}\n")

    print(f"Written to {OUTPUT_FILE}")

    # Categorize and analyze
    categorized, uncategorized = categorize_use_cases(all_use_cases)

    print("\n" + "=" * 70)
    print("USE CASE CATEGORIES")
    print("=" * 70)

    for category, ucs in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{category}: {len(ucs)} mentions")
        # Show unique examples
        unique = list(set(ucs))[:5]
        for uc in unique:
            print(f"  - {uc[:80]}...")

    print(f"\n\nUncategorized: {len(uncategorized)}")

    # Analyze by AI type
    print("\n" + "=" * 70)
    print("USE CASES BY AI TYPE")
    print("=" * 70)

    ai_first_use_cases = [s for s in use_case_sources if s['ai_type'] == 'ai-first']
    ai_support_use_cases = [s for s in use_case_sources if s['ai_type'] == 'ai-support']

    print(f"\nAI-First: {len(ai_first_use_cases)} use cases")
    print(f"AI-Support: {len(ai_support_use_cases)} use cases")

    # Most common words in use cases
    print("\n" + "=" * 70)
    print("MOST COMMON WORDS IN USE CASES")
    print("=" * 70)

    word_counter = Counter()
    for uc in all_use_cases:
        words = uc.lower().split()
        for word in words:
            if len(word) > 3:  # Skip short words
                word_counter[word] += 1

    # Filter out common words
    common_words = {'with', 'from', 'they', 'have', 'been', 'development',
                    'building', 'working', 'including', 'support', 'within'}
    for word in common_words:
        word_counter.pop(word, None)

    for word, count in word_counter.most_common(30):
        print(f"  {word}: {count}")


if __name__ == '__main__':
    main()
