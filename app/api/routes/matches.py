from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.resume import Resume
from app.models.user import User
from app.schemas.match import (
    MatchCreate,
    MatchResponse,
    BatchMatchCreate,
    BatchMatchResponse,
)
    
from app.services.matching_service import match_resume_to_job


router = APIRouter(prefix="/matches", tags=["'Matching"])

@router.post(
    "/",
    response_model= MatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_match(
    match_data: MatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchResponse:

    # 1. Find a resume owned by the current recruiter.
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == match_data.resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # 2. Find a job owned by the current recruiter.
    job = (
        db.query(Job)
        .filter(
            Job.id == match_data.job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # 3. Calculate the match using the existing service.
    match_data_result = match_resume_to_job(
        resume.extracted_text or "",
        job.required_skills or [],
        job.description or "",
    )

    # 4. Prepare the database record.
    match_result = MatchResult(
        recruiter_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        **match_data_result,
    )

    # 5. Save the result.
    try:
        db.add(match_result)
        db.commit()
        db.refresh(match_result)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the matching result.",
        ) from None

    return match_result



@router.post(
    "/batch",
    response_model=BatchMatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_batch_matches(
    batch_data: BatchMatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BatchMatchResponse:

    # 1. Find the job and verify recruiter ownership.
    job = (
        db.query(Job)
        .filter(
            Job.id == batch_data.job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # 2. Fetch only resumes owned by this recruiter.
    resumes = (
        db.query(Resume)
        .filter(
            Resume.id.in_(batch_data.resume_ids),
            Resume.user_id == current_user.id,
        )
        .all()
    )

    # Reject the entire batch if any resume is missing or unauthorized.
    if len(resumes) != len(batch_data.resume_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more resumes were not found.",
        )

    # 3. Calculate and prepare each match result.
    results = []

    try:
        for resume in resumes:
            match_data_result = match_resume_to_job(
                resume.extracted_text or "",
                job.required_skills or [],
                job.description or "",
            )

            match_result = MatchResult(
                recruiter_id=current_user.id,
                resume_id=resume.id,
                job_id=job.id,
                **match_data_result,
            )

            results.append(match_result)

        # 4. Save the entire batch in one transaction.
        db.add_all(results)
        db.commit()

        # Refresh to retrieve database-generated values, such as IDs.
        for result in results:
            db.refresh(result)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the batch matching results.",
        ) from None
        
        
    # 5. Rank candidates by hybrid score, then skill score
    # then semantic score, and finally resume id
    results.sort(
        key=lambda result: (
            -result.hybrid_score,
            -result.match_score,
            -result.semantic_score,
            result.resume_id,
        )
    )


    return BatchMatchResponse(
        job_id=job.id,
        total_screened=len(results),
        results=results,
    )





@router.get("/", response_model=list[MatchResponse])
def list_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MatchResponse]:
    matches = (
        db.query(MatchResult)
        .filter(
            MatchResult.recruiter_id == current_user.id
        )
        .order_by(MatchResult.created_at.desc())
        .all()
    )

    return matches


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchResponse:
    match = (
        db.query(MatchResult)
        .filter(
            MatchResult.id == match_id,
            MatchResult.recruiter_id == current_user.id,
        )
        .first()
    )

    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found.",
        )

    return match