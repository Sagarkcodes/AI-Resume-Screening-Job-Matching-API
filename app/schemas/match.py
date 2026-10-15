
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic import field_validator

from app.core.config import settings

class MatchCreate(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    job_id: int
    match_score: float
    semantic_score: float
    hybrid_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    total_required_skills: int
    created_at: datetime
    


class BatchMatchCreate(BaseModel):
    job_id: int = Field(gt=0)
    resume_ids: list[int] = Field(
    min_length=1,
    max_length=settings.MAX_RESUMES_PER_MATCH,
    )

    @field_validator("resume_ids")
    @classmethod
    def validate_unique_resume_ids(cls, resume_ids: list[int]) -> list[int]:
        if any(resume_id <= 0 for resume_id in resume_ids):
            raise ValueError("Resume IDs must be positive integers.")

        if len(resume_ids) != len(set(resume_ids)):
            raise ValueError("Duplicate resume IDs are not allowed.")

        return resume_ids


class BatchMatchResponse(BaseModel):
    job_id: int
    total_screened: int
    results: list[MatchResponse]
