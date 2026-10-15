from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import(
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume import Resume
    from app.models.user import User


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    recruiter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    resume_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    match_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    
    semantic_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    
    hybrid_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    

    matched_skills: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    missing_skills: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    total_required_skills: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    recruiter: Mapped["User"] = relationship()
    resume: Mapped["Resume"] = relationship()
    job: Mapped["Job"] = relationship()
