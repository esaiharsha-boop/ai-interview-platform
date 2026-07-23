import json
import os
import numpy as np
from fastembed import TextEmbedding

# Path to our curated question bank
QUESTION_BANK_PATH = os.path.join(os.path.dirname(__file__), "question_bank.json")

# Fast, lightweight, local embedding model (free, runs locally)
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Where we persist the precomputed embeddings on disk
EMBEDDINGS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "embeddings_cache.json")

_model = None
_index = None  # in-memory cache: {"ids": [...], "questions": [...], "metadatas": [...], "embeddings": np.ndarray}


def get_embedding_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    return _model


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates local embeddings using FastEmbed."""
    model = get_embedding_model()
    return [emb.tolist() for emb in model.embed(texts)]


def load_question_bank() -> list[dict]:
    with open(QUESTION_BANK_PATH, "r") as f:
        return json.load(f)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10  # avoid division by zero
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
    Embeds every question in the question bank using FastEmbed and caches to disk.
    """
    global _index

    try:
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
        try:
            with open(EMBEDDINGS_CACHE_PATH, "w") as f:
                json.dump(cache_data, f)
        except Exception:
            pass

        _index = {
            "ids": cache_data["ids"],
            "questions": cache_data["questions"],
            "metadatas": cache_data["metadatas"],
            "embeddings": _normalize(np.array(embeddings, dtype=np.float32)),
        }
        print(f"Indexed {len(questions)} questions locally.")
    except Exception as err:
        print(f"Warning: RAG index build skipped or failed: {err}")


def _get_index():
    global _index
    if _index is None:
        _index = _load_index_from_cache()
        if _index is None:
            build_index()
    return _index


def retrieve_relevant_questions(query: str, top_k: int = 3) -> list[dict]:
    """
    Embeds the user's query and finds the top-k most semantically similar
    questions from the indexed question bank using cosine similarity.
    Falls back to matching by topic if embedding model is unavailable.
    """
    questions = load_question_bank()
    try:
        index = _get_index()
        if index is not None and len(index.get("embeddings", [])) > 0:
            query_embedding = np.array(get_embeddings([query])[0], dtype=np.float32)
            query_embedding = query_embedding / (np.linalg.norm(query_embedding) or 1e-10)

            similarities = index["embeddings"] @ query_embedding
            top_k_count = min(top_k, len(similarities))
            top_indices = np.argsort(-similarities)[:top_k_count]

            results = []
            for idx in top_indices:
                results.append({
                    "id": index["ids"][idx],
                    "question": index["questions"][idx],
                    "topic": index["metadatas"][idx]["topic"],
                    "difficulty": index["metadatas"][idx]["difficulty"],
                    "distance": float(1.0 - float(similarities[idx])),
                })
            return results
    except Exception as err:
        print(f"Vector search failed ({err}), falling back to direct question bank search.")

    # Fallback: simple topic or keyword match
    query_lower = query.lower()
    matched = [q for q in questions if query_lower in q["topic"].lower() or any(w in q["question"].lower() for w in query_lower.split())]
    if not matched:
        matched = questions
    results = []
    for q in matched[:top_k]:
        results.append({
            "id": q["id"],
            "question": q["question"],
            "topic": q["topic"],
            "difficulty": q["difficulty"],
            "distance": 0.0,
        })
    return results
