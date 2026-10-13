"""Typed contracts for stored data and every AI response."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)


class Skills(StrictModel):
    category: str
    items: list[str]


class Experience(StrictModel):
    company: str
    title: str
    location: str = ''
    start: str = ''
    end: str = ''
    bullets: list[str] = Field(default_factory=list)


class Project(StrictModel):
    name: str
    tech: list[str] = Field(default_factory=list)
    description: str = ''
    bullets: list[str] = Field(default_factory=list)
    link: str = ''


class Education(StrictModel):
    institution: str
    degree: str
    start: str = ''
    end: str = ''
    details: str = ''


class Certification(StrictModel):
    name: str
    issuer: str = ''
    year: str = ''


class Profile(StrictModel):
    name: str = ''
    phone: str = ''
    email: str = ''
    location: str = ''
    linkedin: str = ''
    portfolio: str = ''
    summary: str = ''
    skills: list[Skills] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class CV(StrictModel):
    summary: str
    skills: list[Skills]
    experience: list[Experience]
    projects: list[Project]
    education: list[Education]
    certifications: list[Certification]


class CoverLetter(StrictModel):
    greeting: str
    opening: str
    body_experience: str
    body_skills: str
    closing: str
    sign_off: str

    @model_validator(mode='after')
    def check_generated_length(self, info: ValidationInfo):
        # AI must satisfy the requested range. Human edits remain editable and
        # receive visible length warnings instead of being discarded.
        if info.context and info.context.get('generation'):
            count = len(' '.join(self.model_dump().values()).split())
            if not 250 <= count <= 350:
                raise ValueError('Generated cover letter must contain 250-350 words.')
        return self


class JDAnalysis(StrictModel):
    job_title: str
    company: str
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    experience_level: str
    keywords: list[str]


class Match(StrictModel):
    experience_indices: list[int]
    project_indices: list[int]
    relevant_skills: list[str]
    gaps: list[str]
    rationale: str


class Suggestion(StrictModel):
    kind: Literal['skill', 'experience_bullet', 'project']
    target_index: int | None = None
    category: str = ''
    value: str = ''
    project: Project | None = None
    log_ids: list[int]
    evidence: str


class Suggestions(StrictModel):
    suggestions: list[Suggestion]


class EmailDraft(StrictModel):
    subject: str
    body: str


class ProviderTest(StrictModel):
    ok: bool


SCHEMAS = {'profile': Profile, 'cv': CV, 'cover_letter': CoverLetter,
           'jd': JDAnalysis, 'match': Match, 'suggestions': Suggestions,
           'email': EmailDraft, 'test': ProviderTest}
