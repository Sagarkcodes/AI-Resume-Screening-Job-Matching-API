
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EmploymentType = Literal[
    "Full-time",
    "Part-time",
    "Contract",
    "Internship",
    "Temporary",
]


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=200)
    company: str = Field(min_length=2, max_length=200)
    location: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20)
    required_skills: list[str] = Field(min_length=1, max_length=50)
    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)
    employment_type: EmploymentType

    @model_validator(mode="after")
    def validate_experience_range(self):
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError(
                "Minimum experience cannot exceed maximum experience"
            )

        return self


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=200)
    company: str | None = Field(default=None, min_length=2, max_length=200)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=20)
    required_skills: list[str] | None = Field(
        default=None, min_length=1, max_length=50
    )
    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)
    employment_type: EmploymentType | None = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data):
        if isinstance(data, dict):
            nullable_fields = {"experience_min", "experience_max"}

            for field, value in data.items():
                if value is None and field not in nullable_fields:
                    raise ValueError(
                        f"'{field}' cannot be null."
                    )

        return data

    @model_validator(mode="after")
    def validate_experience_range(self):
        minimum = self.experience_min
        maximum = self.experience_max

        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(
                "Minimum experience cannot exceed maximum experience"
            )

        return self


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recruiter_id: int
    title: str
    company: str
    location: str
    description: str
    required_skills: list[str]
    experience_min: int | None
    experience_max: int | None
    employment_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
