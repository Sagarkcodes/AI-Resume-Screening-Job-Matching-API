from pathlib import Path

from io import BytesIO

from fastapi import status
from reportlab.pdfgen import canvas

from app.models.resume import Resume
from app.models.user import User


def make_pdf(text="Python FastAPI SQLAlchemy"):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 750, text)
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def test_upload_valid_pdf(client, db_session, test_user, monkeypatch, tmp_path):
    from app.api.routes import resumes

    monkeypatch.setattr(resumes, "UPLOAD_DIR", tmp_path)

    pdf_content = make_pdf()

    response = client.post(
        "/resumes/",
        files={
            "file": (
                "resume.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["original_filename"] == "resume.pdf"
    assert data["file_size_bytes"] == len(pdf_content)
    assert data["extracted_characters"] > 0

    saved_resume = db_session.get(resumes.Resume, data["id"])

    assert saved_resume is not None
    assert saved_resume.user_id == test_user.id
    assert "Python FastAPI SQLAlchemy" in saved_resume.extracted_text

    assert list(tmp_path.glob("*.pdf"))


def test_upload_rejects_non_pdf_extension(client, tmp_path, monkeypatch):
    from app.api.routes import resumes

    monkeypatch.setattr(resumes, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/resumes/",
        files={
            "file": (
                "notes.txt",
                b"This is not a PDF",
                "text/plain",
            )
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Only PDF files are allowed."
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_empty_file(client, tmp_path, monkeypatch):
    from app.api.routes import resumes

    monkeypatch.setattr(resumes, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/resumes/",
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "The uploaded file is empty."


def test_upload_rejects_oversized_file(client, tmp_path, monkeypatch):
    from app.api.routes import resumes

    monkeypatch.setattr(resumes, "UPLOAD_DIR", tmp_path)

    oversized_content = b"A" * (resumes.MAX_FILE_SIZE + 1)

    response = client.post(
        "/resumes/",
        files={
            "file": (
                "large.pdf",
                oversized_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json()["detail"] == "File size must not exceed 5 MB."
    assert list(tmp_path.iterdir()) == []



def test_get_resume_returns_own_resume(client, db_session, test_user):
    resume = Resume(
        user_id=test_user.id,
        original_filename="my_resume.pdf",
        file_path="unused.pdf",
        file_size_bytes=100,
        extracted_text="Python FastAPI SQLAlchemy",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    response = client.get(f"/resumes/{resume.id}")

    assert response.status_code == 200
    assert response.json()["original_filename"] == "my_resume.pdf"
    assert response.json()["extracted_text"] == "Python FastAPI SQLAlchemy"





def test_user_cannot_access_another_users_resume(
    client, db_session
):
    other_user = User(
        email="another-user@example.com",
        password_hash="test-hash",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    resume = Resume(
        user_id=other_user.id,
        original_filename="private.pdf",
        file_path="unused.pdf",
        file_size_bytes=100,
        extracted_text="Private resume content",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    response = client.get(f"/resumes/{resume.id}")

    assert response.status_code == 404


def test_user_cannot_delete_another_users_resume(
    client, db_session, tmp_path, monkeypatch
):
    from app.api.routes import resumes as resume_routes

    monkeypatch.setattr(resume_routes, "UPLOAD_DIR", tmp_path)

    other_user = User(
        email="different-user@example.com",
        password_hash="test-hash",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    pdf_path = tmp_path / "private.pdf"
    pdf_path.write_bytes(b"test file")

    resume = Resume(
        user_id=other_user.id,
        original_filename="private.pdf",
        file_path=str(pdf_path),
        file_size_bytes=9,
        extracted_text="Private resume content",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    response = client.delete(f"/resumes/{resume.id}")

    assert response.status_code == 404
    assert pdf_path.exists()
    assert db_session.get(Resume, resume.id) is not None


def test_delete_own_resume_removes_record_and_file(
    client, db_session, test_user, tmp_path
):
    pdf_path = tmp_path / "my_resume.pdf"
    pdf_path.write_bytes(b"test file")

    resume = Resume(
        user_id=test_user.id,
        original_filename="my_resume.pdf",
        file_path=str(pdf_path),
        file_size_bytes=9,
        extracted_text="My resume content",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    response = client.delete(f"/resumes/{resume.id}")

    assert response.status_code == 204
    assert db_session.get(Resume, resume.id) is None
    assert not pdf_path.exists()
