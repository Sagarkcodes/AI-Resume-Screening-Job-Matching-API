# AI Resume Screening & Job Matching API

A recruiter-focused application that helps screen candidate resumes against job descriptions, calculate explainable match scores, and rank candidates based on skill alignment and semantic similarity.

Built with **FastAPI, Python, PostgreSQL, SQLAlchemy, and Sentence Transformers**, this project combines backend API development, database management, authentication, NLP-based matching, automated testing, and a recruiter-facing web interface.

## Project Overview

Recruiters often need to review multiple resumes for a single job opening. Manually comparing every resume against the job requirements can be time-consuming.

This project streamlines that process by allowing recruiters to manage job descriptions, upload candidate resumes, and identify the candidates whose profiles best align with the requirements.

### Key Features

- **Authentication & Security** — User registration and login, password hashing with Argon2id, and JWT-based authentication.
- **Resume Management** — Upload individual or multiple PDF resumes, extract text, and associate resumes with the authenticated recruiter.
- **Job Management** — Create, view, update, and manage job descriptions and their required skills.
- **Hybrid Resume Matching** — Combine skill-based matching with semantic similarity to evaluate resume relevance.
- **Candidate Ranking** — Rank candidates using a weighted matching score.
- **Match History** — Review screening results by job and inspect candidate rankings.
- **Recruiter Dashboard** — Access job management, resume-related workflows, and matching results through a web interface.
- **Database Migrations** — Manage database schema changes with Alembic.
- **Automated Testing** — Validate application behavior using pytest and FastAPI's testing tools.

## How Resume Matching Works

The application uses a hybrid scoring approach to evaluate how well a candidate's resume aligns with a job description.

| Component | Weight |
|---|---:|
| Skill-based matching | 70% |
| Semantic similarity | 30% |

**Hybrid Match Score = (Skill Match Score × 0.70) + (Semantic Similarity Score × 0.30)**

- **Skill-based matching:** Compares relevant skills extracted from the resume and the job requirements, with normalization and skill-alias handling.
- **Semantic similarity:** Uses sentence embeddings to assess contextual similarity between the resume and job description.
- **Candidate ranking:** Orders candidates using their hybrid scores, helping recruiters prioritize relevant profiles.

The score is a relevance indicator, not a guarantee of job performance or a hiring recommendation. Recruiters should review the underlying resume and make the final decision.

## Technology Stack

| Area | Technologies |
|---|---|
| Language | Python 3.10.11 |
| Backend API | FastAPI, Pydantic |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Database migrations | Alembic |
| Authentication | JWT, PyJWT |
| Password security | Argon2id, pwdlib |
| PDF processing | pypdf |
| Semantic matching | Sentence Transformers |
| Frontend | HTML, CSS, Bootstrap, Jinja2 |
| Testing | pytest, HTTPX, FastAPI TestClient |
| API documentation | Swagger UI / OpenAPI |

## Application Workflow

1. A recruiter registers and logs in.
2. The recruiter creates a job description and defines the required skills.
3. The recruiter uploads one or more candidate resumes in PDF format.
4. The application extracts text from the uploaded PDFs.
5. The matching engine evaluates the resumes against the selected job.
6. Candidates are ranked using the hybrid matching score.
7. The recruiter reviews the results and accesses the job-specific screening history.

## Project Structure

AI_Resume_Matcher/
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── web/
│   │   └── routes.py
│   └── main.py
├── migrations/
├── static/
├── templates/
├── tests/
├── uploads/              # Local files; excluded from Git
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md

*The structure above highlights the main application areas; individual files may vary as the project evolves.*

## Getting Started

### Prerequisites

Install the following before running the project:

- Python 3.10.11
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Sagarkcodes/AI-Resume-Screening-Job-Matching-API.git
cd AI-Resume-Screening-Job-Matching-API
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -3.10 -m venv venv
.\venv\Scripts\Activate.ps1
```

If Python 3.10 is not available through the `py` launcher, install it first or use the interpreter's full path.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root using `.env.example` as a template.

Configure your local PostgreSQL connection and JWT settings. For example:

```dotenv
APP_NAME=AI Resume Screening API
APP_ENV=development

DB_HOST=localhost
DB_PORT=5432
DB_NAME=resume_matcher
DB_USER=your_postgres_username
DB_PASSWORD=your_local_postgres_password

JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Replace the example values with your local configuration. Use a strong, private JWT secret and **never commit your `.env` file, real credentials, or uploaded resumes**.

### 5. Create the PostgreSQL database

Create a PostgreSQL database named `resume_matcher` if it does not already exist.

Ensure the database username and password match your local `.env` configuration.

### 6. Apply database migrations

From the project root, run:

```powershell
alembic upgrade head
```

This applies the available Alembic migrations to your configured database.

### 7. Start the application

```powershell
uvicorn app.main:app --reload
```

Open the following URLs in your browser:

- **API documentation:** http://127.0.0.1:8000/docs
- **Alternative API documentation:** http://127.0.0.1:8000/redoc

The recruiter-facing pages are served by the application's web routes.

> Semantic matching may require downloading a pretrained model the first time it runs. An internet connection may be needed for that initial download, depending on the model's local availability.

## Testing

Run the automated test suite from the project root:

```powershell
python -m pytest -q
```

The suite covers application functionality across areas such as authentication, resume handling, job management, and matching.

## API & Web Routes

The application exposes REST API endpoints and recruiter-facing HTML pages.

### Core API resources

| Endpoint | Purpose |
|---|---|
| `/auth/` | Authentication operations |
| `/resumes/` | Resume management and uploads |
| `/jobs/` | Job description management |
| `/matches/` | Create and retrieve matching results |

Use Swagger UI at `/docs` to inspect the exact registered API endpoints, request schemas, and authentication requirements.

### Recruiter web pages

| Route | Purpose |
|---|---|
| `/register` | Recruiter registration |
| `/login` | Recruiter login |
| `/matches/ui` | Match candidates against a selected job |
| `/matches/history` | Review saved matching results |

## Security & File Handling

- Passwords are hashed rather than stored as plaintext.
- JWTs are used for authenticated API access.
- Environment-specific secrets are kept outside version control.
- Resume uploads are restricted to PDF files, with application-level file validation and a size limit.
- Uploaded resumes and local virtual-environment files are excluded from Git.

## Current Scope & Limitations

- The current workflow is designed for recruiters; candidates do not have a separate account or application workflow.
- Matching scores indicate alignment with the supplied job description and are not a substitute for human review.
- Results depend on the information present in the resume and the quality of the job description.
- The application is intended as a portfolio and development project; production deployment requires additional operational and security review.

## Future Improvements

Potential next steps include:

- Docker-based development and deployment.
- Cloud deployment with managed PostgreSQL.
- Improved resume parsing and structured candidate profiles.
- More extensive evaluation of matching quality against labeled examples.
- CI workflows for automated testing.
- Additional monitoring, logging, and production security controls.

## Author

**Sagar Kalyan Kharade**

GitHub: [@Sagarkcodes](https://github.com/Sagarkcodes)

---

*Developed as a backend-focused project exploring API engineering, database design, secure authentication, NLP-based matching, and recruiter workflows.*