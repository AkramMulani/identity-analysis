"""Comparison utilities: cosine similarity and top-k search."""
from typing import List, Tuple
import numpy as np


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    if a.size == 0 or b.size == 0:
        return 0.0
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def find_top_k(query: List[float], candidates: List[Tuple[int, int, List[float]]], top_k: int = 5) -> List[dict]:
    """Candidates is list of tuples (embedding_id, person_id, vector)
    Returns list of dicts with keys: embedding_id, person_id, score
    """

    # brute-force fallback
    scores = []
    for item in candidates:
        # support either (emb_id, person_id, vector) or (emb_id, person_id, photo_id, vector)
        if len(item) == 3:
            emb_id, person_id, vec = item
        elif len(item) >= 4:
            emb_id, person_id, _photo_id, vec = item[0], item[1], item[2], item[3]
        else:
            continue
        s = cosine_similarity(query, vec)
        scores.append((s, emb_id, person_id))
    scores.sort(reverse=True, key=lambda x: x[0])
    out = []
    for s, emb_id, person_id in scores[:top_k]:
        out.append({"embedding_id": emb_id, "person_id": person_id, "score": float(s)})
    return out
