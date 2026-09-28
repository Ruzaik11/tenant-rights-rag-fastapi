from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding
from tokenizers import Tokenizer

from app.core.config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model)


@lru_cache(maxsize=1)
def _tokenizer() -> Tokenizer:
    # fastembed truncates at 512 tokens, so count with an untruncated tokenizer
    return Tokenizer.from_pretrained(settings.embedding_model)


def embed_passages(texts: list[str]) -> np.ndarray:
    return np.array(list(_model().passage_embed(texts)))


def embed_query(text: str) -> np.ndarray:
    # bge models expect an instruction prefix on queries; query_embed adds it
    return next(iter(_model().query_embed(text)))


def count_tokens(text: str) -> int:
    return len(_tokenizer().encode(text).ids)
