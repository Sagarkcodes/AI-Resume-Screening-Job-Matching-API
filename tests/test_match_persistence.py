
from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.resume import Resume


def test_match_result_can_be_saved_and_retrieved(
    db_session,
    test_user,
):
    # 1. Create a resume owned by the test recruiter.
    resume = Resume(
        user_id=test_user.id,
        original_filename="candidate.pdf",
        file_path="uploads/resumes/candidate.pdf",
        file_size_bytes=1024,
        extracted_text="Python developer with FastAPI and SQL experience.",
    )

    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    # 2. Create a job owned by the same recruiter.
    job = Job(
        recruiter_id=test_user.id,
        title="Python Backend Developer",
        company="ABC Technologies",
        location="Pune",
        description="Develop backend APIs using Python and FastAPI.",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        experience_min=0,
        experience_max=2,
        employment_type="Full-time",
        is_active=True,
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 3. Create and save a matching result.
    match = MatchResult(
        recruiter_id=test_user.id,
        resume_id=resume.id,
        job_id=job.id,
        match_score=66.67,
        matched_skills=["Python", "FastAPI"],
        missing_skills=["PostgreSQL"],
        total_required_skills=3,
    )

    db_session.add(match)
    db_session.commit()

    match_id = match.id

    # 4. Expire cached ORM objects to reload from the database.
    db_session.expire_all()

    saved_match = db_session.get(MatchResult, match_id)

    # 5. Verify the persisted values.
    assert saved_match is not None
    assert saved_match.recruiter_id == test_user.id
    assert saved_match.resume_id == resume.id
    assert saved_match.job_id == job.id
    assert saved_match.match_score == 66.67
    assert saved_match.matched_skills == ["Python", "FastAPI"]
    assert saved_match.missing_skills == ["PostgreSQL"]
    assert saved_match.total_required_skills == 3
    assert saved_match.created_at is not None
