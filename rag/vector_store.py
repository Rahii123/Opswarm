"""
OpsSwarm — RAG Pipeline: Qdrant Vector Store Client
=====================================================
Wraps the Qdrant client with OpsSwarm-specific collection
management, upsert, and semantic search operations.

Usage:
    from rag.vector_store import VectorStore
    store = VectorStore()
    await store.search("db connection pool exhausted", collection="runbooks")
"""

from typing import Any

from core.config import settings
from core.exceptions import CollectionNotFoundError, VectorStoreError
from core.logging_config import get_logger

logger = get_logger(__name__)

# Qdrant payload field used for source filtering
PAYLOAD_SOURCE_FIELD = "source"
PAYLOAD_CONTENT_FIELD = "content"
PAYLOAD_METADATA_FIELD = "metadata"


class VectorStore:
    """
    OpsSwarm Qdrant vector store client.
    Manages three collections: runbooks, historical_incidents, rca_knowledge_base.
    Phase 0: Structure and interface defined. Wired up in Phase 3.
    """

    COLLECTIONS = {
        "runbooks": settings.qdrant_collection_runbooks,
        "incidents": settings.qdrant_collection_incidents,
        "rca": settings.qdrant_collection_rca,
    }

    def __init__(self) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key or None,
                prefer_grpc=False,
            )
            self._Distance = Distance
            self._VectorParams = VectorParams
            logger.info("qdrant_connected", host=settings.qdrant_host, port=settings.qdrant_port)
        except ImportError:
            raise VectorStoreError("qdrant-client not installed. Run: pip install qdrant-client")

    def ensure_collections(self) -> None:
        """
        Create all required collections if they don't exist.
        Safe to call repeatedly (idempotent).
        Call once at application startup.
        """
        from qdrant_client.http.models import Distance, VectorParams

        for alias, name in self.COLLECTIONS.items():
            existing = [c.name for c in self._client.get_collections().collections]
            if name not in existing:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("qdrant_collection_created", collection=name)
            else:
                logger.debug("qdrant_collection_exists", collection=name)

    async def search(
        self,
        query_vector: list[float],
        collection: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search against a collection.

        Args:
            query_vector: Embedded query vector.
            collection:   One of 'runbooks', 'incidents', 'rca'.
            top_k:        Number of results to return.
            score_threshold: Minimum cosine similarity score (0-1).
            filters:      Optional payload filters (e.g. {"severity": "CRITICAL"}).

        Returns:
            List of dicts with 'id', 'score', 'content', 'metadata'.
        """
        collection_name = self.COLLECTIONS.get(collection)
        if not collection_name:
            raise CollectionNotFoundError(collection)

        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "content": r.payload.get(PAYLOAD_CONTENT_FIELD, ""),
                "metadata": r.payload.get(PAYLOAD_METADATA_FIELD, {}),
                "source": r.payload.get(PAYLOAD_SOURCE_FIELD, ""),
            }
            for r in results
        ]

    async def upsert(
        self,
        collection: str,
        doc_id: str,
        vector: list[float],
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "",
    ) -> None:
        """
        Insert or update a document in a collection.

        Args:
            collection: One of 'runbooks', 'incidents', 'rca'.
            doc_id:     Unique document ID (use UUID or slugified filename).
            vector:     Pre-computed embedding vector.
            content:    Raw text content to store in payload.
            metadata:   Additional structured metadata.
            source:     Source identifier (filename, URL, etc.).
        """
        from qdrant_client.models import PointStruct

        collection_name = self.COLLECTIONS.get(collection)
        if not collection_name:
            raise CollectionNotFoundError(collection)

        self._client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={
                        PAYLOAD_CONTENT_FIELD: content,
                        PAYLOAD_METADATA_FIELD: metadata or {},
                        PAYLOAD_SOURCE_FIELD: source,
                    },
                )
            ],
        )
        logger.debug("qdrant_upserted", collection=collection_name, doc_id=doc_id)
