"""
ChromaDB-backed vector store for Athanor RAG.
Uses EphemeralClient and GCS snapshots via google-cloud-storage.
"""

import hashlib
import json
import gzip
import logging
from google.cloud import storage
import chromadb

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=project_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"VectorStore ready: {self._collection.count()} docs in '{project_name}'"
        )

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> int:
        """
        Add pre-embedded chunks to the collection.
        chunks: list of {text, source, chunk_index, metadata: dict}
        embeddings: parallel list of embedding vectors
        Deduplicates by MD5 of text.
        """
        if not chunks:
            return 0

        # Calculate md5s and structure data
        new_items = []
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.md5(chunk["text"].encode()).hexdigest()
            # Flatten metadata into strings/ints/floats for chromadb
            meta = {
                "source": chunk.get("metadata", {}).get("source", ""),
                "chunk_index": chunk.get("metadata", {}).get("chunk_index", 0),
            }
            # Add any other metadata flat
            for k, v in chunk.get("metadata", {}).items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
            new_items.append((doc_id, chunk["text"], meta, embeddings[i]))

        # Filter out existing by ID
        existing_ids = set()
        # ChromaDB get can be slow with many IDs, batch if necessary, but
        # EphemeralClient is fast in memory.
        try:
             all_ids = [item[0] for item in new_items]
             result = self._collection.get(ids=all_ids)
             existing_ids.update(result["ids"])
        except Exception:
             pass

        filtered = [item for item in new_items if item[0] not in existing_ids]

        if not filtered:
            return 0

        ids = [item[0] for item in filtered]
        docs = [item[1] for item in filtered]
        metas = [item[2] for item in filtered]
        embeds = [item[3] for item in filtered]

        self._collection.add(
            ids=ids,
            embeddings=embeds,
            documents=docs,
            metadatas=metas,
        )
        return len(filtered)

    def search(self, query_embedding: list[float], top_k: int = 8) -> list[dict]:
        """Returns list of {text, source, score, metadata}."""
        if self._collection.count() == 0:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

        output = []
        if results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                output.append({
                    "text": doc,
                    "source": meta.get("source", ""),
                    "score": 1.0 - dist,  # distance is cosine distance (1 - cosine similarity)
                    "metadata": meta,
                })
        return output

    def save_to_gcs(self, bucket_name: str, project_name: str) -> None:
        """
        Serialize collection via collection.get(include=["documents","metadatas","embeddings"])
        → JSON → gzip → upload to gs://{bucket}/.vectordb/{project}.json.gz
        """
        data = self._collection.get(include=["documents", "metadatas", "embeddings"])
        serialized = json.dumps(data).encode()
        compressed = gzip.compress(serialized)
        gcs = storage.Client()
        bucket = gcs.bucket(bucket_name)
        blob = bucket.blob(f".vectordb/{project_name}.json.gz")
        blob.upload_from_string(compressed, content_type="application/gzip")
        logger.info(f"Saved snapshot to gs://{bucket_name}/.vectordb/{project_name}.json.gz")

    @classmethod
    def load_from_gcs(cls, bucket_name: str, project_name: str) -> "VectorStore":
        """
        Download gs://{bucket}/.vectordb/{project}.json.gz → decompress → load into EphemeralClient.
        Returns loaded VectorStore instance.
        """
        gcs = storage.Client()
        bucket = gcs.bucket(bucket_name)
        blob = bucket.blob(f".vectordb/{project_name}.json.gz")
        compressed = blob.download_as_bytes()
        data = json.loads(gzip.decompress(compressed))
        store = cls(project_name)
        if data.get("ids"):
            store._collection.add(
                ids=data["ids"],
                documents=data["documents"],
                metadatas=data["metadatas"],
                embeddings=data["embeddings"],
            )
        logger.info(f"Loaded snapshot from gs://{bucket_name}/.vectordb/{project_name}.json.gz")
        return store

    @property
    def count(self) -> int:
        return self._collection.count()
