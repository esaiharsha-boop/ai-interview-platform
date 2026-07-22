import json
import os
import numpy as np
from fastembed import TextEmbedding

# Path to our curated question bank (see question_bank.json in this same folder)
QUESTION_BANK_PATH = os.path.join(os.path.dirname(__file__), "question_bank.json")

# A small, fast, fully local embedding model — free, no API key, no internet
# needed after the first run (model weights are downloaded once and cached).
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Where we persist the precomputed embeddings on disk, so we don't have to
# re-embed the question bank every time the app restarts.
EMBEDDINGS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "embeddings_cache.json")

_model = None
_index = None  # in-memory cache: {"ids": [...], "questions": [...], "metadatas": [...], "embeddings": np.ndarray}


def get_embedding_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    return _model


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Runs the local embedding model over a batch of texts. Free, no API call."""
    model = get_embedding_model()
    return [emb.tolist() for emb in model.embed(texts)]


def load_question_bank() -> list[dict]:
    with open(QUESTION_BANK_PATH, "r") as f:
        return json.load(f)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    return matrix / norms


def _load_index_from_cache():
    """Loads the precomputed index from disk into memory, if present."""
    global _index
    if not os.path.exists(EMBEDDINGS_CACHE_PATH):
        return None

    with open(EMBEDDINGS_CACHE_PATH, "r") as f:
        cached = json.load(f)

    _index = {
        "ids": cached["ids"],
        "questions": cached["questions"],
        "metadatas": cached["metadatas"],
        "embeddings": _normalize(np.array(cached["embeddings"], dtype=np.float32)),
    }
    return _index


def build_index(force: bool = False):
    """
    Embeds every question in the question bank (locally, for free) and caches
    the embeddings to disk. Run this once (or whenever the question bank
    changes) to (re)build the index. Set force=True to rebuild regardless.
    """
    global _index

    if not force and os.path.exists(EMBEDDINGS_CACHE_PATH):
        cached = _load_index_from_cache()
        questions = load_question_bank()
        if cached is not None and len(cached["ids"]) >= len(questions):
            print(f"Index already has {len(cached['ids'])} questions cached. Skipping rebuild.")
            return

    questions = load_question_bank()
    texts = [q["question"] for q in questions]
    embeddings = get_embeddings(texts)

    cache_data = {
        "ids": [q["id"] for q in questions],
        "questions": texts,
        "metadatas": [{"topic": q["topic"], "difficulty": q["difficulty"]} for q in questions],
        "embeddings": embeddings,
    }
    with open(EMBEDDINGS_CACHE_PATH, "w") as f:
        json.dump(cache_data, f)

    _index = {
        "ids": cache_data["ids"],
        "questions": cache_data["questions"],
        "metadatas": cache_data["metadatas"],
        "embeddings": _normalize(np.array(embeddings, dtype=np.float32)),
    }
    print(f"Indexed {len(questions)} questions locally (free) and cached to disk.")


def _get_index():
    global _index
    if _index is None:
        _index = _load_index_from_cache()
        if _index is None:
            build_index()
    return _index


def retrieve_relevant_questions(query: str, top_k: int = 3) -> list[dict]:
    """
    Given a query (e.g. a topic, or resume text like 'Python Django REST APIs'),
    returns the top_k most relevant interview questions using semantic similarity search.
    """
    index = _get_index()
    query_embedding = np.array(get_embeddings([query])[0], dtype=np.float32)
    query_embedding = query_embedding / (np.linalg.norm(query_embedding) or 1e-10)

    similarities = index["embeddings"] @ query_embedding
    top_k = min(top_k, len(similarities))
    top_indices = np.argsort(-similarities)[:top_k]

    matches = []
    for i in top_indices:
        matches.append({
            "id": index["ids"][i],
            "question": index["questions"][i],
            "topic": index["metadatas"][i]["topic"],
            "difficulty": index["metadatas"][i]["difficulty"],
            "distance": float(1 - similarities[i]),
        })
    return matches
