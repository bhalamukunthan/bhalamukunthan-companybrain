"""Text -> list of numbers (embedding). Runs locally; nothing is sent to the internet
(except the one-time model download from Hugging Face)."""
import hashlib
import math
import re

from ..config import settings

_model = None
FAKE_DIM = 1024


def _fake_embed(text: str) -> list[float]:
    """Word-hashing vectors. ONLY for fast offline tests; NOT semantic."""
    vec = [0.0] * FAKE_DIM
    for w in re.findall(r"\w+", text.lower()):
        vec[int(hashlib.md5(w.encode()).hexdigest(), 16) % FAKE_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str]) -> list[list[float]]:
    global _model
    if settings.embedding_backend == "fake":
        return [_fake_embed(t) for t in texts]
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
    return _model.encode(texts, normalize_embeddings=True).tolist()
