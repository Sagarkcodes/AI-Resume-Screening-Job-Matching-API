
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.resume import Resume
from app.models.user import User

from fastapi import File, UploadFile


router = APIRouter(prefix="/resumes", tags=["Resumes"])

UPLOAD_DIR = Path("uploads/resumes")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_BULK_FILES = 10


def extract_resume_text(filename: str, content: bytes) -> str:
    """
    Validate a resume PDF and extract its text.

    Shared by single-upload and bulk-upload endpoints.
    """

    # 1. Validate the filename and extension.
    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # 2. Reject empty and oversized uploads.
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must not exceed 5 MB.",
        )

    # 3. Check the PDF signature instead of trusting Content-Type.
    if b"%PDF-" not in content[:1024]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )

    # 4. Extract text before saving anything permanently.
    try:
        reader = PdfReader(BytesIO(content))

        if reader.is_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password-protected PDFs are not supported.",
            )

        # Join the text from each page with newline characters.
        extracted_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()

    except HTTPException:
        raise
    except (PdfReadError, ValueError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The PDF could not be read. Please upload a valid PDF.",
        ) from None

    # 5. Reject PDFs with no extractable text.
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No extractable text found. Scanned PDFs are not supported yet.",
        )

    return extracted_text


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Read at most 5 MB + 1 byte to detect oversized uploads.
    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    extracted_text = extract_resume_text(file.filename, content)

    # Generate our own filename rather than trusting the uploaded filename.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"

    try:
        saved_path.write_bytes(content)

        resume = Resume(
            user_id=current_user.id,
            original_filename=Path(file.filename).name,
            file_path=str(saved_path),
            file_size_bytes=len(content),
            extracted_text=extracted_text,
        )

        db.add(resume)
        db.commit()
        db.refresh(resume)

    except (OSError, SQLAlchemyError):
        db.rollback()
        saved_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the resume.",
        ) from None

    return {
        "id": resume.id,
        "original_filename": resume.original_filename,
        "file_size_bytes": resume.file_size_bytes,
        "extracted_characters": len(resume.extracted_text),
        "created_at": resume.created_at,
        "message": "Resume uploaded successfully.",
    }


@router.post("/bulk")
async def upload_resumes_bulk(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload up to 10 PDF resumes.
    Each file is processed independently.
    """

    # 1. Validate the number of uploaded files.
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload at least one PDF file.",
        )

    if len(files) > MAX_BULK_FILES:
        for file in files:
            await file.close()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A maximum of {MAX_BULK_FILES} files can be uploaded at once.",
        )

    results = []

    # 2. Process each file independently.
    for file in files:
        original_filename = file.filename or "unnamed"

        try:
            content = await file.read(MAX_FILE_SIZE + 1)
        finally:
            await file.close()

        # 3. Reuse the shared PDF validation and extraction helper.
        try:
            extracted_text = extract_resume_text(
                file.filename,
                content,
            )

        except HTTPException as exc:
            results.append(
                {
                    "filename": original_filename,
                    "status": "failed",
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                }
            )
            continue

        saved_path = None

        # 4. Save the PDF and its database record.
        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            saved_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"
            saved_path.write_bytes(content)

            resume = Resume(
                user_id=current_user.id,
                original_filename=Path(original_filename).name,
                file_path=str(saved_path),
                file_size_bytes=len(content),
                extracted_text=extracted_text,
            )

            db.add(resume)
            db.commit()
            db.refresh(resume)

        except (OSError, SQLAlchemyError):
            db.rollback()

            if saved_path is not None:
                try:
                    saved_path.unlink(missing_ok=True)
                except OSError:
                    pass

            results.append(
                {
                    "filename": original_filename,
                    "status": "failed",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "detail": "Could not save the resume.",
                }
            )
            continue

        # 5. Record the successful upload.
        results.append(
            {
                "filename": resume.original_filename,
                "status": "success",
                "id": resume.id,
                "file_size_bytes": resume.file_size_bytes,
                "extracted_characters": len(resume.extracted_text),
                "created_at": resume.created_at,
                "message": "Resume uploaded successfully.",
            }
        )

    # 6. Calculate the batch summary.
    successful_uploads = sum(
        1
        for result in results
        if result["status"] == "success"
    )

    return {
        "total_files": len(files),
        "successful_uploads": successful_uploads,
        "failed_uploads": len(results) - successful_uploads,
        "results": results,
    }


@router.get("/")
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    return [
        {
            "id": resume.id,
            "original_filename": resume.original_filename,
            "file_size_bytes": resume.file_size_bytes,
            "extracted_characters": len(resume.extracted_text),
            "created_at": resume.created_at,
        }
        for resume in resumes
    ]


@router.get("/{resume_id}")
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    return {
        "id": resume.id,
        "original_filename": resume.original_filename,
        "file_size_bytes": resume.file_size_bytes,
        "extracted_text": resume.extracted_text,
        "created_at": resume.created_at,
    }


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    file_path = Path(resume.file_path)

    try:
        # Remove the database record first, inside a transaction.
        db.delete(resume)
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete the resume.",
        ) from None

    # Remove the PDF after the database commit succeeds.
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        # The database record is already deleted.
        # File cleanup can be retried separately if necessary.
        pass

    return None
