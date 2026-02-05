# Styling Guide

This project documents AI Engineering job market research. The styling is different from the ai-bootcamp curriculum - this is research documentation with data tables and analysis.


## Tables

Use tables sparingly. Only for:

- Small comparison tables (2-4 columns, 10 or fewer rows)
- Data that benefits from tabular format

Prefer lists for most content. Large tables are hard to read.


## Formatting

DO NOT use:

- Bold formatting (NO `**text**`)
- Italic formatting (NO `*text*`)
- Horizontal rules (NO `---`)
- ALL CAPS for emphasis

DO use:

- Code ticks for filenames: `jobs/analysis.md`
- Code ticks for code-related terms: `jobs`, `scripts`, `extract_llm.py`
- Proper list formatting (see below)


## Lists

Use blank lines before and after lists.

For simple items:

- Item one
- Item two

For numbered sequences:

1. First step
2. Second step
3. Third step

For items with descriptions:

- Item one - description here
- Item two - description here

For grouped lists with sub-items, use proper nesting:

- Category name
  - Item one
  - Item two
- Another category
  - Item three


## Links

Links with descriptive text:

[Analysis](analysis/analyze.py) - Main analysis script

For multiple links, format as a list:

- [analyze.py](analysis/analyze.py) - Full statistical analysis
- [analyze_patterns.py](analysis/analyze_patterns.py) - Pattern analysis
- [support_roles.py](analysis/support_roles.py) - Support roles analysis


## Headings

H1 (`#`) is used once at the top of each document for the title.

H2 (`##`) is used for main sections.

H3 (`###`) is used for subsections when it makes logical sense to organize content under a main section.


## Numbers

Use percentages with one decimal place for clarity:

- 69.4% instead of 69%
- 12.3% instead of 12%

Use raw counts for small numbers, add percentages for context:

- 621 jobs (69.4%)


## Tone

Write in first person ("I") for research findings:

- "I found 19 roles..." not "The analysis found 19 roles..."
- "This indicates..." not "This suggests..."

Be direct and concrete. Avoid bureaucratic language.

