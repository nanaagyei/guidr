"""Embedding helpers for Guidr search + recommendations."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from src.config import settings

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


class EmbeddingService:
    """Generates embeddings using the most affordable configured provider."""

    def __init__(self) -> None:
        self.provider = settings.embedding_provider
        self.local_model_name = settings.embedding_model
        self.openai_model_name = settings.openai_embedding_model
        self._openai = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key and OpenAI else None

    def embed_text(self, text: str) -> Optional[List[float]]:
        if not text:
            return None
        text = text.strip()
        if not text:
            return None
        if self.provider == "openai" and self._openai:
            response = self._openai.embeddings.create(model=self.openai_model_name, input=text)
            return response.data[0].embedding
        return self._local_embed(text)

    def embed_institution(self, institution) -> Optional[List[float]]:
        parts = [
            institution.name,
            institution.city,
            institution.state_or_province,
            institution.country,
            institution.institution_type,
        ]
        text = " | ".join(filter(None, parts))
        return self.embed_text(text)

    def embed_program(self, program) -> Optional[List[float]]:
        parts = [
            program.name,
            program.degree_level,
            program.field_of_study,
            program.description,
        ]
        text = " | ".join(filter(None, parts))
        return self.embed_text(text)

    def _local_embed(self, text: str) -> Optional[List[float]]:
        if not SentenceTransformer:
            return None
        model = self._get_sentence_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    @lru_cache(maxsize=1)
    def _get_sentence_model(self):
        if not SentenceTransformer:
            raise RuntimeError("sentence-transformers not installed.")
        return SentenceTransformer(self.local_model_name)


embedding_service = EmbeddingService()

