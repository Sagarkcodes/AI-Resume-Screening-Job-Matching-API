
from unittest.mock import patch

from app.services.matching_service import (
    canonicalize_skill,
    match_resume_to_job,
    normalize_skill,
    skill_appears_in_resume,
)


def test_normalize_skill():
    assert normalize_skill("  PYTHON   ") == "python"


def test_skill_aliases():
    assert canonicalize_skill("Postgres") == "postgresql"
    assert canonicalize_skill("PostgreSQL") == "postgresql"


@patch(
    "app.services.matching_service.calculate_semantic_similarity",
    return_value=70.0,
)
def test_successful_skill_matching(mock_semantic_similarity):
    result = match_resume_to_job(
        resume_text="I have experience with Python, FastAPI and SQL.",
        required_skills=["Python", "FastAPI", "SQL", "Docker"],
    )

    assert result["match_score"] == 75.0
    assert result["matched_skills"] == ["Python", "FastAPI", "SQL"]
    assert result["missing_skills"] == ["Docker"]
    assert result["total_required_skills"] == 4
    assert result["semantic_score"] == 70.0


@patch(
    "app.services.matching_service.calculate_semantic_similarity",
    return_value=70.0,
)
def test_alias_matches_required_skill(mock_semantic_similarity):
    result = match_resume_to_job(
        resume_text="Database experience with Postgres.",
        required_skills=["PostgreSQL"],
    )

    assert result["match_score"] == 100.0
    assert result["matched_skills"] == ["PostgreSQL"]
    assert result["missing_skills"] == []
    assert result["semantic_score"] == 70.0


@patch(
    "app.services.matching_service.calculate_semantic_similarity",
    return_value=70.0,
)
def test_duplicate_requirements_are_counted_once(
    mock_semantic_similarity,
):
    result = match_resume_to_job(
        resume_text="I use PostgreSQL.",
        required_skills=["PostgreSQL", "Postgres"],
    )

    assert result["total_required_skills"] == 1
    assert result["match_score"] == 100.0
    assert result["semantic_score"] == 70.0


def test_no_substring_false_positive_for_sql():
    assert not skill_appears_in_resume(
        "SQL",
        "I have experience with NoSQL databases.",
    )


@patch(
    "app.services.matching_service.calculate_semantic_similarity",
    return_value=70.0,
)
def test_empty_resume_marks_all_skills_missing(
    mock_semantic_similarity,
):
    result = match_resume_to_job(
        resume_text="",
        required_skills=["Python", "Docker"],
    )

    assert result["match_score"] == 0.0
    assert result["matched_skills"] == []
    assert result["missing_skills"] == ["Python", "Docker"]
    assert result["semantic_score"] == 70.0


@patch(
    "app.services.matching_service.calculate_semantic_similarity",
    return_value=70.0,
)
def test_empty_requirements_return_zero_score(
    mock_semantic_similarity,
):
    result = match_resume_to_job(
        resume_text="Python developer",
        required_skills=[],
    )

    assert result["match_score"] == 0.0
    assert result["matched_skills"] == []
    assert result["missing_skills"] == []
    assert result["total_required_skills"] == 0
    assert result["semantic_score"] == 70.0
