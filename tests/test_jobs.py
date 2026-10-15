
from fastapi import status

from app.models.job import Job
from app.models.user import User


def create_test_job(db_session, recruiter_id, **overrides):
    data = {
        "title": "Python Backend Developer",
        "company": "ABC Technologies",
        "location": "Pune",
        "description": (
            "Develop backend APIs using Python and FastAPI "
            "with PostgreSQL."
        ),
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience_min": 0,
        "experience_max": 2,
        "employment_type": "Full-time",
        "is_active": True,
    }
    data.update(overrides)

    job = Job(recruiter_id=recruiter_id, **data)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    return job


def create_other_user(db_session):
    user = User(
        email="another-recruiter@example.com",
        password_hash="test-hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_create_job(client, db_session, test_user):
    response = client.post(
        "/jobs/",
        json={
            "title": "Python Backend Developer",
            "company": "ABC Technologies",
            "location": "Pune",
            "description": (
                "Develop backend APIs using Python and FastAPI."
            ),
            "required_skills": ["Python", "FastAPI"],
            "experience_min": 0,
            "experience_max": 2,
            "employment_type": "Full-time",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["title"] == "Python Backend Developer"
    assert data["recruiter_id"] == test_user.id

    saved_job = db_session.get(Job, data["id"])
    assert saved_job is not None
    assert saved_job.recruiter_id == test_user.id


def test_list_jobs_returns_only_own_jobs(
    client, db_session, test_user
):
    own_job = create_test_job(db_session, test_user.id)

    other_user = create_other_user(db_session)
    create_test_job(
        db_session,
        other_user.id,
        title="Private Recruiter Job",
    )

    response = client.get("/jobs/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == own_job.id


def test_get_own_job(client, db_session, test_user):
    job = create_test_job(db_session, test_user.id)

    response = client.get(f"/jobs/{job.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == job.id
    assert response.json()["title"] == job.title


def test_get_nonexistent_job_returns_404(client):
    response = client.get("/jobs/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_cannot_access_another_recruiters_job(
    client, db_session
):
    other_user = create_other_user(db_session)
    job = create_test_job(db_session, other_user.id)

    response = client.get(f"/jobs/{job.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_own_job(client, db_session, test_user):
    job = create_test_job(db_session, test_user.id)

    response = client.patch(
        f"/jobs/{job.id}",
        json={"title": "Senior Python Developer"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Senior Python Developer"
    assert response.json()["company"] == job.company


def test_user_cannot_update_another_recruiters_job(
    client, db_session
):
    other_user = create_other_user(db_session)
    job = create_test_job(db_session, other_user.id)

    response = client.patch(
        f"/jobs/{job.id}",
        json={"title": "Unauthorized Change"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    db_session.refresh(job)
    assert job.title == "Python Backend Developer"


def test_delete_own_job(client, db_session, test_user):
    job = create_test_job(db_session, test_user.id)

    response = client.delete(f"/jobs/{job.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert db_session.get(Job, job.id) is None


def test_user_cannot_delete_another_recruiters_job(
    client, db_session
):
    other_user = create_other_user(db_session)
    job = create_test_job(db_session, other_user.id)

    response = client.delete(f"/jobs/{job.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert db_session.get(Job, job.id) is not None


def test_create_job_rejects_recruiter_id(
    client, test_user
):
    response = client.post(
        "/jobs/",
        json={
            "title": "Python Backend Developer",
            "company": "ABC Technologies",
            "location": "Pune",
            "description": (
                "Develop backend APIs using Python and FastAPI."
            ),
            "required_skills": ["Python"],
            "employment_type": "Full-time",
            "recruiter_id": test_user.id + 100,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
