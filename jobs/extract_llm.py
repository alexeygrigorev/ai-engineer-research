#!/usr/bin/env python3
"""Extract structured data from job descriptions using Z.ai LLM."""
import os
import yaml
import json
import textwrap
from pathlib import Path
from typing import Literal, Optional, List
from datetime import datetime

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from anthropic import Anthropic

# Load .env file
load_dotenv()

# Directories
SCRIPT_DIR = Path(__file__).parent
EXTRACTED_DIR = SCRIPT_DIR / "extracted"
OUTPUT_DIR = SCRIPT_DIR / "structured"
OUTPUT_DIR.mkdir(exist_ok=True)

# Z.ai client
zai_client = Anthropic(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url="https://api.z.ai/api/anthropic"
)


# ===== YAML HELPERS =====

class LiteralString(str):
    """String that renders with | in YAML for multiline."""
    pass


def represent_literal_string(dumper, data):
    """YAML representer for literal strings."""
    if '\n' in data or len(data) > 60:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(LiteralString, represent_literal_string)


def write_yaml_with_wrapping(data, file):
    """Write YAML with text wrapping for long strings and inline lists for skills."""

    class FlowList(list):
        """List that renders in flow style."""
        pass

    def represent_flow_list(dumper, data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

    yaml.add_representer(FlowList, represent_flow_list)
    yaml.add_representer(LiteralString, represent_literal_string)

    # Fields to wrap: reasoning, use_cases, responsibilities
    wrap_fields = ['reasoning', 'use_cases', 'responsibilities', 'focus']
    # Skill categories
    skill_categories = {'genai', 'ml', 'web', 'databases', 'data', 'cloud', 'ops', 'languages', 'domains', 'other'}

    def _wrap_dict(d, parent_key=''):
        wrapped = {}
        for k, v in d.items():
            key = k
            # Text wrapping for long strings
            if isinstance(v, str) and (k in wrap_fields or any(wf in parent_key for wf in wrap_fields)):
                if len(v) > 60 or '\n' in v:
                    wrapped[k] = LiteralString(textwrap.fill(v, width=60).strip())
                else:
                    wrapped[k] = v
            elif isinstance(v, dict):
                wrapped[k] = _wrap_dict(v, parent_key=k)
            elif isinstance(v, list):
                # Use flow style for skills (under 'skills' key or parent_key is a skill category)
                if k == 'skills' or parent_key in skill_categories or k in skill_categories:
                    wrapped[k] = FlowList(v)
                else:
                    wrapped[k] = [_wrap_dict(item, parent_key=k) if isinstance(item, dict) else item for item in v]
            else:
                wrapped[k] = v
        return wrapped

    wrapped_data = _wrap_dict(data)

    with open(file, 'w', encoding='utf-8') as f:
        yaml.dump(wrapped_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ===== LLM OUTPUT (FLAT) =====

SkillCategory = Literal['genai', 'ml', 'web', 'databases', 'data', 'cloud', 'ops', 'languages', 'domains', 'other']


class Skill(BaseModel):
    name: str
    category: SkillCategory


class JobExtraction(BaseModel):
    """Flat object returned by LLM."""
    ai_type: Literal['ai-first', 'ml-first', 'ai-support', 'unknown']
    ai_type_reasoning: str
    company_stage: Optional[str] = None
    company_focus: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    is_customer_facing: bool = False
    is_management: bool = False


# ===== FINAL OUTPUT (STRUCTURED) =====

class AIType(BaseModel):
    type: Literal['ai-first', 'ml-first', 'ai-support', 'unknown']
    reasoning: str


class Company(BaseModel):
    name: str
    stage: Optional[str] = None
    focus: Optional[str] = None


class SkillsSummary(BaseModel):
    genai: List[str] = Field(default_factory=list)
    ml: List[str] = Field(default_factory=list)
    web: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    data: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    ops: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    other: List[str] = Field(default_factory=list)


class Position(BaseModel):
    title: str = ""
    ai_type: AIType
    responsibilities: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    skills: SkillsSummary
    is_customer_facing: bool = False
    is_management: bool = False


class StructuredJob(BaseModel):
    """Final structured object saved to YAML."""
    company: Company
    position: Position
    meta: dict = Field(default_factory=dict)


def to_structured(job_id: str, title: str, company_name: str, extraction: JobExtraction, extracted_at: str) -> StructuredJob:
    """Transform flat LLM output into structured final object."""

    skills_by_cat = {cat: [] for cat in ['genai', 'ml', 'web', 'databases', 'data', 'cloud', 'ops', 'languages', 'domains', 'other']}

    for skill in extraction.skills:
        skills_by_cat[skill.category].append(skill.name)

    skills_summary = SkillsSummary(**skills_by_cat)

    return StructuredJob(
        company=Company(
            name=company_name,
            stage=extraction.company_stage,
            focus=extraction.company_focus,
        ),
        position=Position(
            title=title,
            ai_type=AIType(
                type=extraction.ai_type,
                reasoning=extraction.ai_type_reasoning
            ),
            responsibilities=extraction.responsibilities,
            use_cases=extraction.use_cases,
            skills=skills_summary,
            is_customer_facing=extraction.is_customer_facing,
            is_management=extraction.is_management
        ),
        meta={'job_id': job_id, 'extracted_at': extracted_at}
    )


# ===== SYSTEM PROMPT =====

EXTRACTION_SYSTEM_PROMPT = """You are an expert at analyzing job descriptions for AI/ML roles. Extract structured information from the job description.

## AI Type Classification

Classify the role as:
- ai-first: Working directly ON AI/ML systems - building, deploying, fine-tuning LLMs/ML models, implementing RAG/agents, model optimization, inference engineering. This INCLUDES Forward Deployed Engineers who deploy AI solutions to customers.
- ml-first: Working directly ON traditional ML/DL - PyTorch, training, optimization, GPU acceleration, but NOT LLMs/agents
- ai-support: Working NEAR AI but NOT ON AI - data pipelines for ML teams, infrastructure/platforms that SUPPORT AI work, customer success for AI products, general software engineering for AI companies. The role does NOT involve building, training, fine-tuning, or deploying models.
- unknown: Cannot determine

Key distinction:
- ai-first: Hands-on work with models/agents (building, deploying, fine-tuning, optimizing)
- ai-support: Enabling work for others who work on AI (infrastructure, platforms, data, general SWE for AI company)

Note: Customer-facing does NOT mean ai-support. FDEs who deploy AI solutions are ai-first.

## Skills

Extract ALL skills as Skill objects {name: string, category: string}.

Categories:
- genai: LangChain, LangGraph, LlamaIndex, DSPy, Haystack, Semantic Kernel, OpenAI/Anthropic APIs, AutoGen, CrewAI, Phidata, Instructor, Marvin, Guardrails, prompt engineering, RAG, agents, function calling, MCP, PEFT, LoRA
- ml: PyTorch, TensorFlow, Keras, JAX, scikit-learn, XGBoost, LightGBM, huggingface, model training, fine-tuning, CUDA
- web: FastAPI, Flask, Django, REST, GraphQL, gRPC, Protobuf, OpenAPI, React, Vue, Next.js
- databases: Postgres, MySQL, Redis, MongoDB, vector DBs (Pinecone, Weaviate, Chroma, Qdrant, Milvus, Faiss, pgvector), Snowflake, BigQuery
- data: Spark, Databricks, Kafka, Airflow, dbt, Prefect, Dagster, Ray, ETL, data pipelines
- cloud: AWS, Azure, GCP, AI services (Bedrock, SageMaker, Vertex AI, Azure AI Studio)
- ops: MLflow, Kubeflow, W&B, Docker, Kubernetes, Terraform, CI/CD, monitoring (Datadog, Prometheus, Grafana, Arize, LangSmith), VLLM, Triton, TensorRT, inference/serving
- languages: Python, TypeScript, Java, Go, Rust, C++, C#, SQL, Scala
- domains: CV, NLP, RL, robotics, diffusion models (ONLY when primary focus)
- other: Anything else

## Responsibilities

Extract as 4-8 bullet points covering key responsibilities.

CRITICAL FORMAT REQUIREMENTS:
- Each item MUST be a plain string starting with text, NOT a bullet point
- WRONG: "- Build AI systems" or "* Build AI systems" or " - Build AI systems"
- CORRECT: "Build AI systems"

## Use Cases

What the AI/ML system actually DOES - the application domain and problem it solves. Extract as 3-6 bullet points.

CRITICAL FORMAT REQUIREMENTS:
- Each item MUST be a plain string starting with text, NOT a bullet point
- WRONG: "- Enterprise search" or "* Enterprise search" or " - Enterprise search"
- CORRECT: "Enterprise search"

## AI Type Reasoning

Write 2-3 sentences maximum explaining the classification. Be concise.

## Company Info

Extract if mentioned:
- company_stage: Seed, Series A, Series B, Public, etc.
- company_focus: What the company does in 5-10 words
"""


# ===== EXTRACTION FUNCTION =====

def extract_from_job(title: str, company: str, description: str) -> JobExtraction:
    """Extract structured data from a job description using Z.ai."""

    user_prompt = f"""Job Title: {title}
Company: {company}

Description:
{description}

Extract the structured information as specified.

IMPORTANT: Return valid JSON objects for nested fields (company_info, responsibilities, skills).
Do NOT return JSON strings - return actual objects/dicts."""

    structured_output_tool = {
        "name": "job_extraction",
        "description": "Extracted job information",
        "input_schema": JobExtraction.model_json_schema()
    }

    max_retries = 3
    for attempt in range(max_retries):
        response = zai_client.messages.create(
            model="glm-4.7",
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[structured_output_tool],
            tool_choice={"type": "tool", "name": structured_output_tool['name']}
        )

        # Parse the tool output - Z.ai may return nested JSON strings
        tool_input = response.content[0].input
        if isinstance(tool_input, dict):
            # Check if any values are JSON strings that need parsing
            parsed_input = {}
            for key, value in tool_input.items():
                if isinstance(value, str):
                    try:
                        parsed_input[key] = json.loads(value)
                    except:
                        parsed_input[key] = value
                else:
                    parsed_input[key] = value
            tool_input = parsed_input

        try:
            extraction = JobExtraction.model_validate(tool_input)
            return extraction
        except Exception as e:
            print(f"  Validation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise

    raise Exception("Failed to extract valid output after retries")


def extract_job(yaml_file: Path) -> tuple[str | None, dict | None]:
    """Extract structured data from a job YAML file.

    Returns:
        tuple: (output_filename, structured_data_dict)
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        job = yaml.safe_load(f)

    job_id = str(job.get('job_id', ''))
    title = job.get('title', '')
    company = job.get('company', '')
    description = job.get('description', '')

    print(f"Processing: {title} at {company}")

    # Extract using LLM
    try:
        extraction = extract_from_job(title, company, description)
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None

    # Transform to structured output
    structured = to_structured(
        job_id=job_id,
        title=title,
        company_name=company,
        extraction=extraction,
        extracted_at=datetime.now().isoformat()
    )

    # Generate output filename
    output_filename = yaml_file.name  # same name, different directory

    print(f"  AI Type: {extraction.ai_type}")
    print(f"  Skills: {len(extraction.skills)}")

    return output_filename, structured.model_dump()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enrich jobs with LLM extraction')
    parser.add_argument('yaml_file', nargs='?', help='Specific YAML file to process')
    parser.add_argument('--all', action='store_true', help='Process all YAML files')
    parser.add_argument('--limit', type=int, help='Limit number of files to process')
    args = parser.parse_args()

    if not os.getenv("ZAI_API_KEY"):
        print("Error: ZAI_API_KEY environment variable not set")
        return

    if args.yaml_file:
        # Process single file
        yaml_file = Path(args.yaml_file)
        if not yaml_file.exists():
            print(f"File not found: {yaml_file}")
            return

        output_filename, output = extract_job(yaml_file)
        if output:
            output_file = OUTPUT_DIR / output_filename
            write_yaml_with_wrapping(output, output_file)

            print(f"\nSaved: {output_file}")

    elif args.all:
        # Process all files
        yaml_files = list(EXTRACTED_DIR.glob("*.yaml"))
        if args.limit:
            yaml_files = yaml_files[:args.limit]

        print(f"Processing {len(yaml_files)} YAML files...\n")

        results = {'ai-first': 0, 'ml-first': 0, 'ai-support': 0, 'unknown': 0}
        errors = []
        skipped = 0

        for i, yaml_file in enumerate(yaml_files, 1):
            output_filename = yaml_file.name
            output_file = OUTPUT_DIR / output_filename

            # Skip if already processed
            if output_file.exists():
                skipped += 1
                continue

            try:
                output_filename, output = extract_job(yaml_file)
                if output:
                    write_yaml_with_wrapping(output, output_file)

                    results[output['position']['ai_type']['type']] += 1

                    print(f"[{i}/{len(yaml_files)}] {yaml_file.name[:50]}... -> {output['position']['ai_type']['type']}")
            except Exception as e:
                errors.append((yaml_file.name, str(e)))
                print(f"[{i}/{len(yaml_files)}] {yaml_file.name[:50]}... ERROR: {e}")

        print(f"\n{'='*60}")
        print(f"Results:")
        print(f"  AI-First: {results['ai-first']}")
        print(f"  ML-First: {results['ml-first']}")
        print(f"  AI-Support: {results['ai-support']}")
        print(f"  Unknown: {results['unknown']}")
        print(f"  Skipped: {skipped}")
        print(f"  Errors: {len(errors)}")

        if errors:
            print(f"\nErrors:")
            for name, err in errors[:5]:
                print(f"  {name}: {err}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
