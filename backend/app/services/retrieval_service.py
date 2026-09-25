import time
from typing import List, Dict, Any, Optional, Tuple
from backend.app.config import settings
from backend.app.logger import logger
from backend.app.services.embedding_service import embedding_service
from backend.app.services.vector_store import vector_store
from backend.app.schemas.query import SourceReference


class RetrievalService:
    def __init__(self):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[SourceReference], float]:
        """
        Retrieves top_k relevant text chunks for the query.
        
        Returns:
            Tuple of:
            - raw_chunks: List[Dict[str, Any]]
            - source_references: List[SourceReference]
            - latency_ms: float
        """
        start_time = time.perf_counter()
        k = top_k or settings.TOP_K

        # Check if vector store has any records
        if self.vector_store.count() == 0:
            logger.info("Vector store is empty. 0 chunks retrieved.")
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return [], [], round(elapsed_ms, 2)

        # 1. Embed user query
        query_embedding = self.embedding_service.embed_query(query)

        # 2. Search vector store
        matched_chunks = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
            document_id=document_id
        )

        # 3. Format structured source references
        sources: List[SourceReference] = []
        for chunk in matched_chunks:
            # Generate a 150-char snippet preview
            raw_text = chunk.get("text", "")
            snippet = raw_text[:140] + ("..." if len(raw_text) > 140 else "")
            
            sources.append(
                SourceReference(
                    document=chunk.get("filename", "unknown.pdf"),
                    document_id=chunk.get("document_id", ""),
                    page=int(chunk.get("page_number", 1)),
                    chunk_id=chunk.get("chunk_id", ""),
                    relevance_score=chunk.get("relevance_score"),
                    snippet=snippet
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Retrieved {len(matched_chunks)} chunks for query in {elapsed_ms:.2f}ms "
            f"(top_k={k}, doc_filter={document_id})"
        )

        return matched_chunks, sources, round(elapsed_ms, 2)


retrieval_service = RetrievalService()
