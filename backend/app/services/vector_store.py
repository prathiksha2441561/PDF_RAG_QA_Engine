import math
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.logger import logger


class VectorStore:
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self._client = None
        self._collection = None
        self._memory_chunks: List[Dict[str, Any]] = []
        self._memory_embeddings: List[List[float]] = []
        self._init_store()

    def _init_store(self) -> None:
        """Initializes ChromaDB persistent client or falls back to in-memory store."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            # Create or get collection
            self._collection = self._client.get_or_create_collection(
                name="pdf_documents",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB initialized at '{self.persist_dir}'. Current count: {self._collection.count()}")
        except Exception as e:
            logger.warning(
                f"Could not initialize ChromaDB persistent client: {str(e)}. "
                "Using in-memory vector store."
            )
            self._client = None
            self._collection = None

    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """Adds text chunks with embeddings and metadata to the vector store."""
        if not chunks:
            return

        if self._collection is not None:
            ids = [c["chunk_id"] for c in chunks]
            documents = [c["text"] for c in chunks]
            metadatas = [
                {
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "page_number": int(c["page_number"]),
                    "chunk_id": c["chunk_id"]
                }
                for c in chunks
            ]
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Upserted {len(chunks)} chunks into ChromaDB.")
        else:
            # In-memory store
            for chunk, emb in zip(chunks, embeddings):
                # Update existing if chunk_id matches
                existing_idx = next((i for i, c in enumerate(self._memory_chunks) if c["chunk_id"] == chunk["chunk_id"]), None)
                if existing_idx is not None:
                    self._memory_chunks[existing_idx] = chunk
                    self._memory_embeddings[existing_idx] = emb
                else:
                    self._memory_chunks.append(chunk)
                    self._memory_embeddings.append(emb)
            logger.info(f"Stored {len(chunks)} chunks in in-memory vector store.")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most similar chunks for the given query vector.
        Optionally filters by document_id.
        """
        results: List[Dict[str, Any]] = []

        if self._collection is not None:
            where_filter = {"document_id": document_id} if document_id else None
            # Ensure top_k does not exceed total items in collection
            total_items = self._collection.count()
            if total_items == 0:
                return []
            k = min(top_k, total_items)

            try:
                chroma_res = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )

                if chroma_res["ids"] and len(chroma_res["ids"][0]) > 0:
                    ids = chroma_res["ids"][0]
                    docs = chroma_res["documents"][0]
                    metas = chroma_res["metadatas"][0]
                    distances = chroma_res["distances"][0] if "distances" in chroma_res else [0.0] * len(ids)

                    for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
                        # Cosine distance in Chroma: similarity = 1 - distance
                        similarity = max(0.0, 1.0 - float(dist)) if dist is not None else 1.0
                        results.append({
                            "chunk_id": chunk_id,
                            "document_id": meta.get("document_id", ""),
                            "filename": meta.get("filename", ""),
                            "page_number": int(meta.get("page_number", 1)),
                            "text": text,
                            "relevance_score": round(similarity, 4)
                        })
            except Exception as e:
                logger.error(f"Error querying ChromaDB: {str(e)}")
                return []
        else:
            # Memory cosine similarity search
            if not self._memory_chunks:
                return []

            filtered_indices = [
                i for i, c in enumerate(self._memory_chunks)
                if not document_id or c["document_id"] == document_id
            ]
            if not filtered_indices:
                return []

            scored = []
            q_vec = query_embedding
            for idx in filtered_indices:
                emb = self._memory_embeddings[idx]
                dot = sum(a * b for a, b in zip(q_vec, emb))
                norm_q = math.sqrt(sum(a * a for a in q_vec)) or 1e-9
                norm_e = math.sqrt(sum(b * b for b in emb)) or 1e-9
                sim = dot / (norm_q * norm_e)
                scored.append((sim, self._memory_chunks[idx]))

            scored.sort(key=lambda x: x[0], reverse=True)
            for sim, chunk in scored[:top_k]:
                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "filename": chunk["filename"],
                    "page_number": int(chunk["page_number"]),
                    "text": chunk["text"],
                    "relevance_score": round(float(sim), 4)
                })

        return results

    def delete_document(self, document_id: str) -> None:
        """Deletes all chunks belonging to a document."""
        if self._collection is not None:
            self._collection.delete(where={"document_id": document_id})
        else:
            indices_to_remove = [
                i for i, c in enumerate(self._memory_chunks)
                if c["document_id"] == document_id
            ]
            for i in reversed(indices_to_remove):
                del self._memory_chunks[i]
                del self._memory_embeddings[i]

    def count(self) -> int:
        if self._collection is not None:
            return self._collection.count()
        return len(self._memory_chunks)


vector_store = VectorStore()
