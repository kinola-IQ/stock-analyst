"""Pinecone-backed storage utilities with an in-memory fallback.

This module provides a simple `PineconeStorage` wrapper that encapsulates
initialization, upsert, query, fetch, and delete operations. If Pinecone
is not available or API credentials are missing, an in-memory fallback is
used so callers can continue to operate in offline or test environments.

Environment variables supported:
- `PINECONE_API_KEY` (required for Pinecone)
- `PINECONE_ENV` (Pinecone environment/region)
- `PINECONE_INDEX` (index name)
"""
from typing import Any, Dict, List, Optional, Tuple
import os
import logging

logger = logging.getLogger(__name__)


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
        self._environment = environment or os.getenv("PINECONE_ENV")
        self._index_name = (
            index_name or os.getenv("PINECONE_INDEX", "stock-analyst")
        )
        self._dimension = dimension

        self._enabled = False
        self._index = None
        self._pinecone = None
        self._in_memory: Dict[str, Dict[str, Any]] = {}

        if not self._api_key:
            logger.info(
                "Pinecone API key not provided; using in-memory storage."
            )
            return

        try:
            import pinecone  # type: ignore

            self._pinecone = pinecone
        except ImportError:
            logger.exception(
                "Failed to import Pinecone client; using in-memory storage."
            )
            return

        try:
            # Initialize Pinecone client
            self._pinecone.init(
                api_key=self._api_key, environment=self._environment
            )

            # Create index if it doesn't exist
            if self._index_name not in self._pinecone.list_indexes():
                self._pinecone.create_index(
                    name=self._index_name, dimension=self._dimension
                )

            self._index = self._pinecone.Index(self._index_name)
            self._enabled = True
            logger.info(
                "Pinecone storage initialized: index=%s", self._index_name
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.exception(
                "Failed to initialize Pinecone index; falling back to in-memory storage."
            )
            logger.debug("Pinecone init error: %s", exc)

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
                self._index.upsert([(vector_id, vector, metadata or {})])
                return
            except Exception:
                logger.exception(
                    "Pinecone upsert failed; falling back to in-memory store."
                )

        # in-memory fallback
        self._in_memory[vector_id] = {"vector": vector, "metadata": metadata or {}}

    def fetch(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a vector and metadata by id."""
        if self._enabled and self._index is not None:
            try:
                resp = self._index.fetch([vector_id])
                # Pinecone returns a dict with 'vectors'
                vectors = (
                    resp.get("vectors")
                    if isinstance(resp, dict)
                    else getattr(resp, "vectors", None)
                )
                if not vectors:
                    return None
                data = vectors.get(vector_id)
                return data
            except Exception:
                logger.exception(
                    "Pinecone fetch failed; falling back to in-memory store."
                )

        return self._in_memory.get(vector_id)

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query nearest vectors to `vector` and return list of results.

        Each result is a dict containing `id`, `score`, and optional `metadata`.
        """
        if self._enabled and self._index is not None:
            try:
                resp = self._index.query(
                    vector=vector,
                    top_k=top_k,
                    include_metadata=include_metadata,
                )
                # resp.matches is a list of matches in many SDKs
                matches = []
                if isinstance(resp, dict):
                    for m in resp.get("matches", []):
                        matches.append(m)
                else:
                    matches = getattr(resp, "matches", []) or []
                return matches
            except Exception:
                logger.exception(
                    "Pinecone query failed; falling back to in-memory similarity search."
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
                out.append(
                    {"id": _id, "score": score, "metadata": rec.get("metadata", {})}
                )
            return out
        except Exception:
            logger.exception("In-memory query failed.")
            return []

    def delete(self, vector_id: str) -> None:
        """Delete vector by id."""
        if self._enabled and self._index is not None:
            try:
                self._index.delete(ids=[vector_id])
                return
            except Exception:
                logger.exception(
                    "Pinecone delete failed; falling back to in-memory delete."
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
            except Exception:
                logger.exception(
                    "Pinecone list ids failed; falling back to in-memory list."
                )

        return list(self._in_memory.keys())

    def close(self) -> None:
        """Close resources if needed."""
        try:
            if self._enabled and self._pinecone is not None:
                # Some SDKs require explicit deinit; this is best-effort.
                if hasattr(self._pinecone, "deinit"):
                    self._pinecone.deinit()
        except Exception:
            logger.exception("Failed to close Pinecone client cleanly.")


# Convenience default instance
default_storage = PineconeStorage()
