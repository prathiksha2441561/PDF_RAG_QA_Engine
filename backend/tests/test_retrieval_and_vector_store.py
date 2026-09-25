import pytest
from backend.app.services.vector_store import vector_store
from backend.app.services.embedding_service import embedding_service
from backend.app.services.retrieval_service import retrieval_service


def test_vector_store_add_and_search():
    sample_chunks = [
        {
            "chunk_id": "test_chunk_1",
            "document_id": "doc_alpha",
            "filename": "alpha.pdf",
            "page_number": 1,
            "text": "The quick brown fox jumps over the lazy dog."
        },
        {
            "chunk_id": "test_chunk_2",
            "document_id": "doc_beta",
            "filename": "beta.pdf",
            "page_number": 2,
            "text": "Quantum computing utilizes superposition and entanglement."
        }
    ]

    embeddings = embedding_service.embed_texts([c["text"] for c in sample_chunks])
    vector_store.add_chunks(sample_chunks, embeddings)

    # Search for quantum
    query_emb = embedding_service.embed_query("quantum superposition")
    results = vector_store.search(query_emb, top_k=1)

    assert len(results) == 1
    assert results[0]["chunk_id"] == "test_chunk_2"
    assert "superposition" in results[0]["text"]


def test_retrieval_service_wrapper():
    chunks, sources, latency_ms = retrieval_service.retrieve(
        query="superposition",
        top_k=2
    )
    assert len(sources) >= 1
    assert latency_ms > 0
    assert sources[0].document in ("beta.pdf", "cloud_architecture_specification.pdf", "alpha.pdf")
