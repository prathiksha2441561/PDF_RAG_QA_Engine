import pytest
from backend.app.services.chunking_service import ChunkingService


def test_chunking_basic():
    chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "The quick brown fox jumps over the lazy dog. "
        "Artificial intelligence and retrieval augmented generation are powerful concepts. "
        "Vector databases index high-dimensional embeddings for fast semantic nearest neighbor search."
    )
    chunks = chunker.chunk_page_text(
        text=sample_text,
        document_id="doc-123",
        filename="test.pdf",
        page_number=1
    )
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["document_id"] == "doc-123"
        assert chunk["filename"] == "test.pdf"
        assert chunk["page_number"] == 1
        assert "chunk_id" in chunk
        assert len(chunk["text"]) <= 150  # Boundary-aware margin


def test_chunking_empty_text():
    chunker = ChunkingService()
    chunks = chunker.chunk_page_text("", "doc-1", "test.pdf", 1)
    assert chunks == []


def test_chunking_invalid_overlap():
    with pytest.raises(ValueError):
        ChunkingService(chunk_size=100, chunk_overlap=120)
