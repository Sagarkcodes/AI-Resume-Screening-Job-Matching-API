import re

from app.services.semantic_matching_service import(
    calculate_semantic_similarity
)


#Common aliases for the same technology
SKILL_ALIASES = {
    "postgresql" : ["postgresql", "postgres"],
    "javascript": ["javascript", "js"],
    "node.js": ["node.js", "nodejs"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
}



def normalize_skill(skill: str) -> str:
    """Normalize a skill name for consistent comparison."""
    return " ".join(skill.lower().strip().split())



def canonicalize_skill(skill: str) -> str:
    """Convert known aliases to a single canonical skill name."""
    normalized = normalize_skill(skill)
    
    for canonical, aliases in SKILL_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized
    

def skill_appears_in_resume(skill: str, resume_text: str) -> bool:
    """Check whether a skill appears as a phrase, not a substring."""
    normalized_skill = canonicalize_skill(skill)

    aliases = SKILL_ALIASES.get(
        normalized_skill, [normalized_skill]
    )

    for alias in aliases:
        # Allow flexible whitespace in multi-word skills.
        escaped_alias = re.escape(alias)
        pattern = escaped_alias.replace(r"\ ", r"\s+")

        # Avoid matching a skill inside a longer word.
        if re.search(
            rf"(?<![a-zA-Z0-9]){pattern}(?![a-zA-Z0-9])",
            resume_text,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def match_resume_to_job(
    resume_text: str,
    required_skills: list[str],
    job_description: str = "",
) -> dict:
    """Calculate explainable skill coverage for a resume and job."""
    unique_skills = []
    seen_skills = set()

    for skill in required_skills:
        if not skill or not skill.strip():
            continue

        canonical = canonicalize_skill(skill)

        if canonical not in seen_skills:
            seen_skills.add(canonical)
            unique_skills.append((skill.strip(), canonical))

    matched_skills = []
    missing_skills = []

    for display_name, canonical in unique_skills:
        if skill_appears_in_resume(canonical, resume_text):
            matched_skills.append(display_name)
        else:
            missing_skills.append(display_name)

    total = len(unique_skills)

    score = round(
        len(matched_skills) / total * 100,
        2,
    ) if total else 0.0
    
    
    
    

    
    
    # Use the full job description when available.
    # Fall back to required skills for existing callers.
    job_text = job_description.strip()

    if not job_text:
        job_text = "Required skills: " + ", ".join(
            display_name for display_name, _ in unique_skills
        )

    semantic_score = calculate_semantic_similarity(
        resume_text,
        job_text,
    )
    
    # Combine skill coverage and semantic similarity.
    hybrid_score = round(
        (0.70 * score) + (0.30 * semantic_score),
        2,
    )


    return {
        "match_score": score,
        "semantic_score": semantic_score,
        "hybrid_score": hybrid_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_required_skills": total,
    }