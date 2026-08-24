from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding
from tokenizers import Tokenizer

from app.core.config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    # Downloads the model on first use, then loads from cache
    return TextEmbedding(model_name=settings.embedding_model)


@lru_cache(maxsize=1)
def _tokenizer() -> Tokenizer:
    # Separate tokenizer with no truncation, so counts above 512 are real
    return Tokenizer.from_pretrained(settings.embedding_model)


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embed law text. Returns shape (n, 384), each row normalized."""
    return np.array(list(_model().passage_embed(texts)))


def embed_query(text: str) -> np.ndarray:
    """Embed one user question. Returns shape (384,)."""
    return np.array(list(_model().query_embed(text))[0])


def count_tokens(text: str) -> int:
    return len(_tokenizer().encode(text).ids)


def fits(text: str) -> bool:
    """True if the text fits in one chunk."""
    return count_tokens(text) <= settings.max_chunk_tokens


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


if __name__ == "__main__":
    sentences = [
        "A landlord shall not increase the rent without giving at least 90 days written notice.",
        "The landlord must tell the tenant in writing three months before raising the rent.",
        "A landlord may require a rent deposit equal to one month's rent.",
        "The tenant is responsible for ordinary cleanliness of the rental unit.",
        "My landlord gave me a note saying rent goes up next month.",
    ]

    vectors = embed_passages(sentences)
    print("Shape:", vectors.shape)
    print("Norm of first vector:", round(float(np.linalg.norm(vectors[0])), 4))
    print()

    print("Similarity to sentence 0:")
    for i, s in enumerate(sentences[1:], start=1):
        print(f"  {cosine(vectors[0], vectors[i]):.3f}  {s}")
    print()

    q = embed_query("How much notice does my landlord need to raise rent?")
    print("Query vs each passage:")
    for s, v in sorted(zip(sentences, vectors), key=lambda p: -cosine(q, p[1])):
        print(f"  {cosine(q, v):.3f}  {s}")
    print()

    for s in sentences[:2]:
        print(f"{count_tokens(s):>3} tokens  fits={fits(s)}  {s}")