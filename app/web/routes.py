from pathlib import Path

from fastapi import (
    APIRouter, 
    Depends, 
    File, 
    Form, 
    Request,
    HTTPException,
    UploadFile,
    status,
)

from uuid import uuid4

from app.core.config import settings

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin
from app.services.auth_service import register_user, authenticate_user

from app.api.dependencies import get_current_user_from_cookie

from app.models.job import Job
from app.schemas.job import JobCreate

from sqlalchemy.exc import SQLAlchemyError

from app.models.resume import Resume

from app.api.routes.resumes import(
    extract_resume_text,
    UPLOAD_DIR,
    MAX_FILE_SIZE,
    MAX_BULK_FILES,
)

from app.models.match_result import MatchResult
from app.services.matching_service import match_resume_to_job



router = APIRouter(tags=["Web Pages"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)



@router.get("/", include_in_schema=False)
def home_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={}
    )


@router.get("/register", include_in_schema=False)
def register_page(
    request: Request,
    registered: bool = False,
):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "registered": registered,
        },
    )


@router.post("/register", include_in_schema=False)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user_data = UserRegister(
            email=email,
            password=password,
        )
    except ValidationError:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": (
                    "Please enter a valid email and a password "
                    "between 8 and 128 characters."
                ),
            },
            status_code=400,
        )

    try:
        register_user(db, user_data)
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": str(exc),
            },
            status_code=409,
        )

    return RedirectResponse(
        url="/register?registered=true",
        status_code=303,
    )
    


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user_data = UserLogin(
            email=email,
            password=password,
        )
    except ValidationError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Please enter a valid email address.",
            },
            status_code=400,
        )

    try:
        access_token = authenticate_user(db, user_data)
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Incorrect email or password.",
            },
            status_code=401,
        )

    response = RedirectResponse(
        url="/dashboard",
        status_code=303,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return response



@router.get("/dashboard", include_in_schema=False)
def dashboard_page(
    request: Request,
    current_user=Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user,
        },
    )
    
    

@router.post("/logout", include_in_schema=False)
def logout():
    response = RedirectResponse(
        url="/login",
        status_code=303,
    )

    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )

    return response



@router.get("/jobs", include_in_schema=False)
def jobs_page(
    request: Request,
    deleted: bool = False,
    delete_error: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    jobs = (
        db.query(Job)
        .filter(Job.recruiter_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )

    error = None
    message = None

    if deleted:
        message = "Job deleted successfully."

    if delete_error:
        error = (
            "The job could not be deleted. It may have related "
            "matching records. Please review the job's dependencies."
        )

    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "jobs": jobs,
            "error": error,
            "message": message,
        },
    )
 

 
# Display resumes uploaded by the logged-in recruiter
@router.get("/resumes/manage", include_in_schema=False)
def resumes_page(
    request: Request,
    deleted: bool = False,
    delete_error: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    message = None
    error = None

    if deleted:
        message = "Resume deleted successfully."

    if delete_error:
        error = (
            "The resume could not be deleted. "
            "Please try again."
        )

    return templates.TemplateResponse(
        request=request,
        name="resumes.html",
        context={
            "resumes": resumes,
            "message": message,
            "error": error,
        },
    )
 


# Display saved matching results for the logged-in recruiter
# Display saved matching results grouped by job
@router.get("/matches/history", include_in_schema=False)
def match_history_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    matches = (
        db.query(MatchResult)
        .filter(MatchResult.recruiter_id == current_user.id)
        .order_by(
            MatchResult.created_at.desc(),
            MatchResult.id.desc(),
        )
        .all()
    )

    # Keep the latest result for each resume within each job.
    latest_by_job_and_resume = {}

    for match in matches:
        key = (match.job_id, match.resume_id)

        if key not in latest_by_job_and_resume:
            latest_by_job_and_resume[key] = match

    # Group the latest results by job.
    grouped_matches = {}

    for match in latest_by_job_and_resume.values():
        grouped_matches.setdefault(match.job_id, []).append(match)

    # Rank candidates using the existing ranking rules.
    for job_matches in grouped_matches.values():
        job_matches.sort(
            key=lambda match: (
                -match.hybrid_score,
                -match.match_score,
                -match.semantic_score,
                match.resume_id,
            )
        )

    # Order job groups by their most recent saved result.
    job_groups = []

    for job_id, job_matches in grouped_matches.items():
        job_groups.append({
            "job": job_matches[0].job,
            "matches": job_matches,
            "candidate_count": len(job_matches),
            "latest_activity": max(
                match.created_at for match in job_matches
            ),
        })

    job_groups.sort(
        key=lambda group: group["latest_activity"],
        reverse=True,
    )

    return templates.TemplateResponse(
        request=request,
        name="match_history.html",
        context={
            "user": current_user,
            "job_groups": job_groups,
            "matches": matches,
        },
    )






# Display the Match Candidates page
@router.get("/matches/ui", include_in_schema=False)
def match_candidates_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    # Load only jobs owned by the logged-in recruiter.
    jobs = (
        db.query(Job)
        .filter(Job.recruiter_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )

    # Load only resumes owned by the logged-in recruiter.
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="match_candidates.html",
        context={
            "user": current_user,
            "jobs": jobs,
            "resumes": resumes,
            "max_resumes": settings.MAX_RESUMES_PER_MATCH,
        },
    )



@router.post("/matches/ui", include_in_schema=False)
def run_matching_from_ui(
    request: Request,
    job_id: int = Form(...),
    resume_ids: list[int] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    # Validate the selected job belongs to this recruiter.
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Enforce the batch limit and reject duplicate IDs.
    if (
        not 1 <= len(resume_ids) <= settings.MAX_RESUMES_PER_MATCH
        or len(resume_ids) != len(set(resume_ids))
        or any(resume_id <= 0 for resume_id in resume_ids)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Select between 1 and "
                f"{settings.MAX_RESUMES_PER_MATCH} unique resumes"
            ),
        )

    # Fetch only resumes owned by this recruiter.
    resumes = (
        db.query(Resume)
        .filter(
            Resume.id.in_(resume_ids),
            Resume.user_id == current_user.id,
        )
        .all()
    )

    if len(resumes) != len(resume_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more resumes were not found.",
        )

    results = []

    try:
        for resume in resumes:
            scores = match_resume_to_job(
                resume.extracted_text or "",
                job.required_skills or [],
                job.description or "",
            )

            result = MatchResult(
                recruiter_id=current_user.id,
                resume_id=resume.id,
                job_id=job.id,
                **scores,
            )

            results.append(result)

        db.add_all(results)
        db.commit()

        for result in results:
            db.refresh(result)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the matching results.",
        ) from None

    # Use the same ranking rules as the existing batch API.
    results.sort(
        key=lambda result: (
            -result.hybrid_score,
            -result.match_score,
            -result.semantic_score,
            result.resume_id,
        )
    )

    # Reload the page data for rendering.
    jobs = (
        db.query(Job)
        .filter(Job.recruiter_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )

    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    resume_lookup = {resume.id: resume for resume in resumes}

    return templates.TemplateResponse(
        request=request,
        name="match_candidates.html",
        context={
            "user": current_user,
            "jobs": jobs,
            "resumes": resumes,
            "selected_job_id": job.id,
            "selected_resume_ids": resume_ids,
            "results": results,
            "resume_lookup": resume_lookup,
            "screened_count": len(results),
            "max_resumes": settings.MAX_RESUMES_PER_MATCH,
        },
    )





# Upload one or multiple resumes through the browser
@router.post("/resumes/manage", include_in_schema=False)
async def resumes_upload_submit(
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    results = []

    # Reject an empty selection or too many files.
    if not files or len(files) > MAX_BULK_FILES:
        for file in files:
            await file.close()

        resumes = (
            db.query(Resume)
            .filter(Resume.user_id == current_user.id)
            .order_by(Resume.created_at.desc())
            .all()
        )

        return templates.TemplateResponse(
            request=request,
            name="resumes.html",
            context={
                "resumes": resumes,
                "error": (
                    f"Please select between 1 and {MAX_BULK_FILES} files."
                ),
            },
            status_code=400,
        )

    # Process each file independently.
    for file in files:
        filename = file.filename or "unnamed"

        try:
            content = await file.read(MAX_FILE_SIZE + 1)
        finally:
            await file.close()

        try:
            extracted_text = extract_resume_text(filename, content)

        except HTTPException as exc:
            results.append({
                "filename": filename,
                "status": "failed",
                "detail": str(exc.detail),
            })
            continue

        saved_path = None

        try:
            # Store the PDF using a generated filename.
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            saved_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"
            saved_path.write_bytes(content)

            # Create a database record for the logged-in recruiter.
            resume = Resume(
                user_id=current_user.id,
                original_filename=Path(filename).name,
                file_path=str(saved_path),
                file_size_bytes=len(content),
                extracted_text=extracted_text,
            )

            db.add(resume)
            db.commit()

            results.append({
                "filename": resume.original_filename,
                "status": "success",
            })

        except (OSError, SQLAlchemyError):
            db.rollback()

            if saved_path is not None:
                try:
                    saved_path.unlink(missing_ok=True)
                except OSError:
                    pass

            results.append({
                "filename": filename,
                "status": "failed",
                "detail": "Could not save the resume.",
            })

    # Fetch the updated list for the same page.
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    successful_uploads = sum(
        result["status"] == "success"
        for result in results
    )

    return templates.TemplateResponse(
        request=request,
        name="resumes.html",
        context={
            "resumes": resumes,
            "results": results,
            "successful_uploads": successful_uploads,
            "failed_uploads": len(results) - successful_uploads,
        },
    )


# Delete a resume from the browser UI
@router.post("/resumes/{resume_id}/delete", include_in_schema=False)
def resume_delete_submit(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    # Find the resume and verify ownership.
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    # Do not delete a resume belonging to another recruiter.
    if resume is None:
        return RedirectResponse(
            url="/resumes/manage?delete_error=true",
            status_code=303,
        )

    # Remember the PDF path before deleting the database record.
    file_path = Path(resume.file_path)

    try:
        db.delete(resume)
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        return RedirectResponse(
            url="/resumes/manage?delete_error=true",
            status_code=303,
        )

    # Remove the stored PDF after the database deletion succeeds.
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        # The database record is already deleted.
        # A leftover file can be cleaned up separately.
        pass

    return RedirectResponse(
        url="/resumes/manage?deleted=true",
        status_code=303,
    )


# Find a resume belonging to the logged-in recruiter
def get_owned_resume(
    resume_id: int,
    db: Session,
    current_user,
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
            status_code=404,
            detail="Resume not found.",
        )

    # Check that the original PDF still exists.
    if not Path(resume.file_path).is_file():
        raise HTTPException(
            status_code=404,
            detail="The stored resume PDF could not be found.",
        )

    return resume


# View a resume in the browser
@router.get(
    "/resumes/{resume_id}/view",
    include_in_schema=False,
)
def resume_view(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    resume = get_owned_resume(
        resume_id,
        db,
        current_user,
    )

    return FileResponse(
        path=resume.file_path,
        media_type="application/pdf",
        filename=resume.original_filename,
        content_disposition_type="inline",
    )


# Download the original resume PDF
@router.get(
    "/resumes/{resume_id}/download",
    include_in_schema=False,
)
def resume_download(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    resume = get_owned_resume(
        resume_id,
        db,
        current_user,
    )

    return FileResponse(
        path=resume.file_path,
        media_type="application/pdf",
        filename=resume.original_filename,
        content_disposition_type="attachment",
    )


  


# Delete an existing job
@router.post("/jobs/{job_id}/delete", include_in_schema=False)
def job_delete_submit(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    # Find the job belonging to the logged-in recruiter.
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    # Do not delete a job that does not belong to this recruiter.
    if job is None:
        return RedirectResponse(
            url="/jobs",
            status_code=303,
        )

    try:
        db.delete(job)
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        return RedirectResponse(
            url="/jobs?delete_error=true",
            status_code=303,
        )

    return RedirectResponse(
        url="/jobs?deleted=true",
        status_code=303,
    )



# View individual job details
@router.get("/jobs/{job_id}/details", include_in_schema=False)
def job_details_page(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    if job is None:
        return RedirectResponse(
            url="/jobs",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="job_details.html",
        context={
            "job": job,
        },
    )



# Open the edit form for an existing job
@router.get("/jobs/{job_id}/edit", include_in_schema=False)
def job_edit_page(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    if job is None:
        return RedirectResponse(
            url="/jobs",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="job_edit.html",
        context={
            "job": job,
            "form": {},
        },
    )
    


# Save changes to an existing job
@router.post("/jobs/{job_id}/edit", include_in_schema=False)
def job_edit_submit(
    request: Request,
    job_id: int,
    title: str = Form(...),
    company: str = Form(...),
    location: str = Form(...),
    description: str = Form(...),
    required_skills: str = Form(...),
    employment_type: str = Form(...),
    experience_min: str = Form(default=""),
    experience_max: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    # Find the job and verify recruiter ownership.
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.recruiter_id == current_user.id,
        )
        .first()
    )

    if job is None:
        return RedirectResponse(
            url="/jobs",
            status_code=303,
        )

    # Preserve submitted values if validation fails.
    form = {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "required_skills": required_skills,
        "employment_type": employment_type,
        "experience_min": experience_min,
        "experience_max": experience_max,
    }

    try:
        minimum = int(experience_min) if experience_min.strip() else None
        maximum = int(experience_max) if experience_max.strip() else None

        skills = [
            skill.strip()
            for skill in required_skills.split(",")
            if skill.strip()
        ]

        job_data = JobCreate(
            title=title,
            company=company,
            location=location,
            description=description,
            required_skills=skills,
            employment_type=employment_type,
            experience_min=minimum,
            experience_max=maximum,
        )

    except (ValidationError, ValueError):
        return templates.TemplateResponse(
            request=request,
            name="job_edit.html",
            context={
                "job": job,
                "form": form,
                "error": (
                    "Please check your job details, required skills, "
                    "and experience range. Minimum experience cannot "
                    "exceed maximum experience."
                ),
            },
            status_code=400,
        )

    # Update the existing database record.
    for field, value in job_data.model_dump().items():
        setattr(job, field, value)

    try:
        db.commit()
        db.refresh(job)

    except SQLAlchemyError:
        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="job_edit.html",
            context={
                "job": job,
                "form": form,
                "error": "Could not update the job. Please try again.",
            },
            status_code=500,
        )

    return RedirectResponse(
        url=f"/jobs/{job.id}/details",
        status_code=303,
    )


 
#Create jobs     
@router.get("/jobs/create", include_in_schema=False)
def job_create_page(
    request: Request,
    current_user=Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse(
        request=request,
        name="job_create.html",
        context={},
    )


@router.post("/jobs/create", include_in_schema=False)
def job_create_submit(
    request: Request,
    title: str = Form(...),
    company: str = Form(...),
    location: str = Form(...),
    description: str = Form(...),
    required_skills: str = Form(...),
    employment_type: str = Form(...),
    experience_min: str = Form(default=""),
    experience_max: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    try:
        minimum = int(experience_min) if experience_min.strip() else None
        maximum = int(experience_max) if experience_max.strip() else None

        skills = [
            skill.strip()
            for skill in required_skills.split(",")
            if skill.strip()
        ]

        job_data = JobCreate(
            title=title,
            company=company,
            location=location,
            description=description,
            required_skills=skills,
            employment_type=employment_type,
            experience_min=minimum,
            experience_max=maximum,
        )

    except (ValidationError, ValueError):
        return templates.TemplateResponse(
            request=request,
            name="job_create.html",
            context={
                "error": (
                    "Please check your job details, skills, and "
                    "experience range. Minimum experience cannot "
                    "exceed maximum experience."
                ),
            },
            status_code=400,
        )

    job = Job(
        **job_data.model_dump(),
        recruiter_id=current_user.id,
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)

    except SQLAlchemyError:
        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="job_create.html",
            context={
                "error": "Could not save the job. Please try again.",
            },
            status_code=500,
        )

    return RedirectResponse(
        url="/jobs",
        status_code=303,
    )
    
    
    


