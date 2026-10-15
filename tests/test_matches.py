
from fastapi import status

from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.resume import Resume
from app.models.user import User


def create_test_resume(db_session, user_id, text):
    resume = Resume(
        user_id=user_id,
        original_filename="candidate.pdf",
        file_path="uploads/resumes/candidate.pdf",
        file_size_bytes=1024,
        extracted_text=text,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


def create_test_job(db_session, recruiter_id):
    job = Job(
        recruiter_id=recruiter_id,
        title="Python Backend Developer",
        company="ABC Technologies",
        location="Pune",
        description="Develop APIs using Python and FastAPI.",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        experience_min=0,
        experience_max=2,
        employment_type="Full-time",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def create_other_user(db_session):
    user = User(
        email="other-recruiter@example.com",
        password_hash="test-hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_match(client, db_session, test_user):
    resume = create_test_resume(
        db_session,
        test_user.id,
        "Python developer with FastAPI experience.",
    )
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/",
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["resume_id"] == resume.id
    assert data["job_id"] == job.id
    assert data["match_score"] == 66.67
    assert data["matched_skills"] == ["Python", "FastAPI"]
    assert data["missing_skills"] == ["PostgreSQL"]
    assert data["total_required_skills"] == 3

    saved_result = db_session.get(MatchResult, data["id"])
    assert saved_result is not None
    assert saved_result.recruiter_id == test_user.id


def test_match_rejects_another_recruiters_resume(
    client, db_session, test_user
):
    other_user = create_other_user(db_session)

    resume = create_test_resume(
        db_session,
        other_user.id,
        "Python and FastAPI",
    )
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/",
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_match_rejects_another_recruiters_job(
    client, db_session, test_user
):
    other_user = create_other_user(db_session)

    resume = create_test_resume(
        db_session,
        test_user.id,
        "Python and FastAPI",
    )
    job = create_test_job(db_session, other_user.id)

    response = client.post(
        "/matches/",
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_match_rejects_nonexistent_resume(client, db_session, test_user):
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/",
        json={
            "resume_id": 999999,
            "job_id": job.id,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_match_rejects_nonexistent_job(client, db_session, test_user):
    resume = create_test_resume(
        db_session,
        test_user.id,
        "Python and FastAPI",
    )

    response = client.post(
        "/matches/",
        json={
            "resume_id": resume.id,
            "job_id": 999999,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND



def test_list_matches_returns_own_results(
    client, db_session, test_user
):
    resume = create_test_resume(
        db_session,
        test_user.id,
        "Python developer with FastAPI experience.",
    )
    job = create_test_job(db_session, test_user.id)

    client.post(
        "/matches/",
        json={"resume_id": resume.id, "job_id": job.id},
    )

    response = client.get("/matches/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["resume_id"] == resume.id
    assert data[0]["job_id"] == job.id


def test_list_matches_excludes_other_recruiters_results(
    client, db_session, test_user
):
    resume = create_test_resume(
        db_session,
        test_user.id,
        "Python developer with FastAPI experience.",
    )
    job = create_test_job(db_session, test_user.id)

    client.post(
        "/matches/",
        json={"resume_id": resume.id, "job_id": job.id},
    )

    other_user = create_other_user(db_session)
    other_resume = create_test_resume(
        db_session,
        other_user.id,
        "Java developer.",
    )
    other_job = create_test_job(
        db_session, other_user.id
    )

    client.post(
        "/matches/",
        json={
            "resume_id": other_resume.id,
            "job_id": other_job.id,
        },
    )

    response = client.get("/matches/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["resume_id"] == resume.id



def test_get_own_match(client, db_session, test_user):
    resume = create_test_resume(
        db_session,
        test_user.id,
        "Python developer with FastAPI experience.",
    )
    job = create_test_job(db_session, test_user.id)

    create_response = client.post(
        "/matches/",
        json={"resume_id": resume.id, "job_id": job.id},
    )
    match_id = create_response.json()["id"]

    response = client.get(f"/matches/{match_id}")

    assert response.status_code == 200
    assert response.json()["id"] == match_id
    assert response.json()["resume_id"] == resume.id
    assert response.json()["job_id"] == job.id


def test_get_nonexistent_match_returns_404(client):
    response = client.get("/matches/999999")

    assert response.status_code == 404
    
    
    
def test_user_cannot_access_another_recruiters_match(
    client, db_session
):
    other_user = create_other_user(db_session)
    resume = create_test_resume(
        db_session,
        other_user.id,
        "Java developer.",
    )
    job = create_test_job(db_session, other_user.id)

    # Create the result directly because the test client
    # authenticates as the original test_user.
    from app.models.match_result import MatchResult
    from app.services.matching_service import match_resume_to_job

    result_data = match_resume_to_job(
        resume.extracted_text,
        job.required_skills,
    )
    match = MatchResult(
        recruiter_id=other_user.id,
        resume_id=resume.id,
        job_id=job.id,
        **result_data,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    response = client.get(f"/matches/{match.id}")

    assert response.status_code == 404
    
    

def test_batch_match_creates_and_ranks_results(
    client, db_session, test_user
):
    lower_match_resume = create_test_resume(
        db_session,
        test_user.id,
        "Python developer.",
    )
    higher_match_resume = create_test_resume(
        db_session,
        test_user.id,
        "Python FastAPI PostgreSQL developer.",
    )
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/batch",
        json={
            "job_id": job.id,
            "resume_ids": [
                lower_match_resume.id,
                higher_match_resume.id,
            ],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["job_id"] == job.id
    assert data["total_screened"] == 2
    assert len(data["results"]) == 2

    
    # Results must be ranked by hybrid score, highest first.
    assert (
        data["results"][0]["hybrid_score"]
        >= data["results"][1]["hybrid_score"]
    )

    # The candidate with the higher hybrid score should rank first.
    assert (
        data["results"][0]["resume_id"]
        == higher_match_resume.id
    )


    # Confirm both results were persisted.
    for result in data["results"]:
        saved_result = db_session.get(MatchResult, result["id"])
        assert saved_result is not None
        assert saved_result.recruiter_id == test_user.id


def test_batch_match_rejects_nonexistent_resume(
    client, db_session, test_user
):
    resume = create_test_resume(
        db_session, test_user.id, "Python developer."
    )
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/batch",
        json={
            "job_id": job.id,
            "resume_ids": [resume.id, 999999],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_batch_match_rejects_more_than_fifty_resumes(
    client, db_session, test_user
):
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/batch",
        json={
            "job_id": job.id,
            "resume_ids": list(range(1, 52)),
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_batch_match_rejects_another_recruiters_job(
    client, db_session, test_user
):
    resume = create_test_resume(
        db_session, test_user.id, "Python developer."
    )
    other_user = create_other_user(db_session)
    job = create_test_job(db_session, other_user.id)

    response = client.post(
        "/matches/batch",
        json={
            "job_id": job.id,
            "resume_ids": [resume.id],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_batch_match_rejects_duplicate_resume_ids(
    client, db_session, test_user
):
    resume = create_test_resume(
        db_session, test_user.id, "Python developer."
    )
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/batch",
        json={
            "job_id": job.id,
            "resume_ids": [resume.id, resume.id],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT




def test_batch_match_rejects_empty_resume_list(client, db_session, test_user):
    job = create_test_job(db_session, test_user.id)

    response = client.post(
        "/matches/batch",
        json={
            "job_id": job.id,
            "resume_ids": [],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
