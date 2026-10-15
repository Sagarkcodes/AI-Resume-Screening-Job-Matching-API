
from app.services.semantic_matching_service import (
    calculate_semantic_similarity,
)


def test_empty_resume_returns_zero():
    assert calculate_semantic_similarity(
        "",
        "Looking for a Python backend developer.",
    ) == 0.0


def test_empty_job_description_returns_zero():
    assert calculate_semantic_similarity(
        "Experienced Python developer.",
        "",
    ) == 0.0


def test_similar_texts_produce_a_valid_score():
    score = calculate_semantic_similarity(
        "Developed backend web services and REST APIs using Python.",
        "Build REST APIs and backend services using Python.",
    )

    assert 0.0 <= score <= 100.0




def test_relevant_resume_scores_higher_than_unrelated_resume():
    job_description = (
        "We need a Python backend developer experienced in "
        "building REST APIs, database integration, and web services."
    )

    relevant_resume = (
        "Developed Python backend applications, built REST APIs, "
        "integrated databases, and maintained web services."
    )

    unrelated_resume = (
        "Experienced graphic designer specializing in logo design, "
        "visual branding, typography, and image editing."
    )

    relevant_score = calculate_semantic_similarity(
        relevant_resume,
        job_description,
    )

    unrelated_score = calculate_semantic_similarity(
        unrelated_resume,
        job_description,
    )

    assert relevant_score > unrelated_score
