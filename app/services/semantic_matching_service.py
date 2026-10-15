from functools import lru_cache

from sentence_transformers import SentenceTransformer, util


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_semantic_model() -> SentenceTransformer:
    """Load the pretrained model once and reuse it"""
    return SentenceTransformer(MODEL_NAME)


def calculate_semantic_similarity(
    resume_text: str,
    job_description: str,
) -> float:
    """
    Calculate semantic similarity between resume and job description.
    
    Returns a similarity score frim 0 to 100
    """
    if not resume_text.strip() or not job_description.strip():
        return 0.0
    
    model = get_semantic_model()
    
    embeddings = model.encode(
        [resume_text, job_description],
        convert_to_tensor=True,
        normalize_embeddings=True,
    )
    
    similarity = util.cos_sim(
        embeddings[0],
        embeddings[1],
    ).item()
    
    #Convert cosine similarity to a percentage-like score
    return round(max(0.0, min(1.0, similarity)) * 100, 2) 