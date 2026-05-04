"""
OpsSwarm — RAG Pipeline: Embedding Abstraction
===============================================
Provides a unified interface for generating embeddings
regardless of the underlying provider (Gemini, OpenAI, Ollama).

Usage:
    from rag.embeddings import get_embedder
    embedder = get_embedder()
    vector = await embedder.embed("DB connection pool exhausted")
"""

from abc import ABC, abstractmethod
from typing import Sequence

from core.config import settings
from core.exceptions import LLMError
from core.logging_config import get_logger

logger = get_logger(__name__)


class BaseEmbedder(ABC):
    """Abstract base class for all embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single string. Returns a float vector."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple strings. Returns a list of float vectors."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension size."""
        ...


class GeminiEmbedder(BaseEmbedder):
    """Google Gemini embedding provider."""

    def __init__(self) -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._model = settings.embedding_model
            self._genai = genai
        except ImportError:
            raise LLMError("google-generativeai package not installed. Run: pip install google-generativeai")

    async def embed(self, text: str) -> list[float]:
        logger.debug("embedding_text", provider="gemini", model=self._model, text_len=len(text))
        result = self._genai.embed_content(model=self._model, content=text)
        return result["embedding"]

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        return settings.embedding_dimension


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embedding provider."""

    def __init__(self) -> None:
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            self._model = settings.embedding_model
        except ImportError:
            raise LLMError("openai package not installed. Run: pip install openai")

    async def embed(self, text: str) -> list[float]:
        logger.debug("embedding_text", provider="openai", model=self._model)
        response = await self._client.embeddings.create(input=text, model=self._model)
        return response.data[0].embedding

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(input=list(texts), model=self._model)
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return 1536  # text-embedding-3-small default


_embedder_cache: BaseEmbedder | None = None


def get_embedder() -> BaseEmbedder:
    """
    Factory — returns the configured embedder singleton.
    Caches the instance after first call.
    """
    global _embedder_cache
    if _embedder_cache is not None:
        return _embedder_cache

    provider = settings.embedding_provider
    logger.info("initialising_embedder", provider=provider)

    if provider == "gemini":
        _embedder_cache = GeminiEmbedder()
    elif provider == "openai":
        _embedder_cache = OpenAIEmbedder()
    else:
        raise LLMError(f"Unsupported embedding provider: '{provider}'. Use 'gemini' or 'openai'.")

    return _embedder_cache
