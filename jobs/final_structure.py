from typing import Literal, Optional, List
from pydantic import BaseModel, Field


# ===== LLM OUTPUT (FLAT) =====

class Skill(BaseModel):
    name: str
    category: Literal['genai', 'ml', 'web', 'databases', 'data', 'cloud', 'ops', 'languages', 'domains', 'other']


class JobExtraction(BaseModel):
    """Flat object returned by LLM."""
    ai_type: Literal['ai-first', 'ml-first', 'ai-support', 'unknown']
    ai_type_reasoning: str
    company_stage: Optional[str] = None
    company_focus: Optional[str] = None
    responsibilities: str = ""
    use_cases: str = ""
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
    use_cases: str = ""  # What the AI/ML system actually does


class SkillsByCategory(BaseModel):
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


class SkillsSummary(BaseModel):
    all: List[str] = Field(default_factory=list)
    by_category: SkillsByCategory
    count: int = 0


class StructuredJob(BaseModel):
    """Final structured object saved to YAML."""
    job_id: str
    title: str

    ai_type: AIType

    company: Company

    responsibilities: str

    skills: SkillsSummary

    is_customer_facing: bool
    is_management: bool

    extracted_at: str


# ===== TRANSFORMATION FUNCTION =====

def to_structured(job_id: str, title: str, company_name: str, extraction: JobExtraction, extracted_at: str) -> StructuredJob:
    """Transform flat LLM output into structured final object."""

    # Group skills by category
    by_category = SkillsByCategory()
    all_skills = []

    for skill in extraction.skills:
        by_category.__dict__[skill.category].append(skill.name)
        all_skills.append(skill.name)

    skills_summary = SkillsSummary(
        all=all_skills,
        by_category=by_category,
        count=len(all_skills)
    )

    return StructuredJob(
        job_id=job_id,
        title=title,
        ai_type=AIType(
            type=extraction.ai_type,
            reasoning=extraction.ai_type_reasoning
        ),
        company=Company(
            name=company_name,
            stage=extraction.company_stage,
            focus=extraction.company_focus,
            use_cases=extraction.use_cases,
        ),
        responsibilities=extraction.responsibilities,
        skills=skills_summary,
        is_customer_facing=extraction.is_customer_facing,
        is_management=extraction.is_management,
        extracted_at=extracted_at
    )
