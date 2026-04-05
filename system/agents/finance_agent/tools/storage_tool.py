"""Pinecone-backed storage utilities with an in-memory fallback.

This module provides a simple `PineconeStorage` wrapper that encapsulates
initialization, upsert, query, fetch, and delete operations. If Pinecone
is not available or API credentials are missing, an in-memory fallback is
used so callers can continue to operate in offline or test environments.

Environment variables supported:
- `PINECONE_API_KEY` (required for Pinecone)
- `PINECONE_ENV` (Pinecone environment/region, e.g., 'us-east-1')
- `PINECONE_INDEX` (index name)
"""
from typing import Any, Dict, List, Optional, Tuple
import os
import logging

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    logger.warning("Pinecone client not available; using in-memory storage.")
    PINECONE_AVAILABLE = False
    Pinecone = None  # type: ignore
    ServerlessSpec = None  # type: ignore


class PineconeStorage:
    """Wrapper around Pinecone index with simple CRUD/query operations.

    If Pinecone is not available (ImportError) or the API key is not set,
    the class falls back to an in-memory dict-based store.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: Optional[str] = None,
        dimension: int = 1536,
    ) -> None:
        self._api_key = api_key or os.getenv("PINECONE_API_KEY")
        self._environment = (
            environment or os.getenv("PINECONE_ENV", "us-east-1")
        )
        self._index_name = (
            index_name or os.getenv("PINECONE_INDEX", "stock-analyst")
        )
        self._dimension = dimension

        self._enabled = False
        self._index = None
        self._pinecone = None
        self._in_memory: Dict[str, Dict[str, Any]] = {}

        if not self._api_key or not PINECONE_AVAILABLE:
            logger.info(
                "Pinecone API key not provided or client unavailable; "
                "using in-memory storage."
            )
            return

        try:
            # Initialize Pinecone client
            self._pinecone = Pinecone(api_key=self._api_key)

            # Check if index exists
            existing_indexes = [
                idx.name for idx in self._pinecone.list_indexes()
            ]
            if self._index_name not in existing_indexes:
                # Create index with serverless spec
                spec = ServerlessSpec(cloud="aws", region=self._environment)
                self._pinecone.create_index(
                    name=self._index_name,
                    dimension=self._dimension,
                    spec=spec
                )

            self._index = self._pinecone.Index(self._index_name)
            self._enabled = True
            logger.info(
                "Pinecone storage initialized: index=%s", self._index_name
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.exception(
                "Failed to initialize Pinecone index; falling back to "
                "in-memory storage. Error: %s", exc
            )

    def upsert(
        self,
        vector_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Upsert a single vector with optional metadata."""
        if self._enabled and self._index is not None:
            try:
                # Pinecone accepts a list of tuples: (id, vector, metadata)
                self._index.upsert(
                    vectors=[(vector_id, vector, metadata or {})]
                )
                return
            except Exception as exc:
                logger.exception(
                    "Pinecone upsert failed; falling back to in-memory store. "
                    "Error: %s", exc
                )

        # in-memory fallback
        self._in_memory[vector_id] = {
            "vector": vector,
            "metadata": metadata or {}
        }

    def fetch(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a vector and metadata by id."""
        if self._enabled and self._index is not None:
            try:
                resp = self._index.fetch(ids=[vector_id])
                # Pinecone returns a dict with 'vectors'
                vectors = resp.get("vectors", {})
                if not vectors:
                    return None
                data = vectors.get(vector_id)
                return data
            except Exception as exc:
                logger.exception(
                    "Pinecone fetch failed; falling back to in-memory store. "
                    "Error: %s", exc
                )

        return self._in_memory.get(vector_id)

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query nearest vectors to `vector` and return list of results.

        Each result is a dict containing `id`, `score`, and optional
        `metadata`.
        """
        if self._enabled and self._index is not None:
            try:
                resp = self._index.query(
                    vector=vector,
                    top_k=top_k,
                    include_metadata=include_metadata,
                )
                # resp.matches is a list of matches
                matches = resp.get("matches", [])
                return matches
            except Exception as exc:
                logger.exception(
                    "Pinecone query failed; falling back to in-memory "
                    "similarity search. Error: %s", exc
                )

        # naive in-memory similarity. Dot-product or cosine is not implemented;
        # use simple negative L2 distance as a scoring heuristic.
        results: List[Tuple[str, float]] = []
        try:
            for _id, rec in self._in_memory.items():
                vec = rec.get("vector")
                if not vec:
                    continue
                # compute simple negative L2 distance as score
                score = -sum((a - b) ** 2 for a, b in zip(vec, vector))
                results.append((_id, score))
            results.sort(key=lambda x: x[1], reverse=True)
            out = []
            for _id, score in results[:top_k]:
                rec = self._in_memory.get(_id, {})
                out.append({
                    "id": _id,
                    "score": score,
                    "metadata": rec.get("metadata", {})
                })
            return out
        except Exception as exc:
            logger.exception("In-memory query failed. Error: %s", exc)
            return []

    def delete(self, vector_id: str) -> None:
        """Delete vector by id."""
        if self._enabled and self._index is not None:
            try:
                self._index.delete(ids=[vector_id])
                return
            except Exception as exc:
                logger.exception(
                    "Pinecone delete failed; falling back to in-memory "
                    "delete. Error: %s", exc
                )

        if vector_id in self._in_memory:
            del self._in_memory[vector_id]

    def list_ids(self) -> List[str]:
        """Return a list of stored ids (best-effort)."""
        if self._enabled and self._index is not None:
            try:
                # Pinecone does not provide a direct 'list ids' in all SDKs.
                # Fetching ids is SDK-dependent; return empty list here.
                return []
            except Exception as exc:
                logger.exception(
                    "Pinecone list ids failed; falling back to in-memory "
                    "list. Error: %s", exc
                )

        return list(self._in_memory.keys())

    def close(self) -> None:
        """Close resources if needed."""
        # Modern Pinecone client handles cleanup automatically


# Convenience default instance
default_storage = PineconeStorage()
