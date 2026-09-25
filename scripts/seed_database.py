import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.services.pdf_service import PDFService
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.embedding_service import embedding_service
from backend.app.services.vector_store import vector_store
from backend.app.models.database import db
from backend.app.logger import logger


def seed():
    pdf_path = Path(root_dir) / "documents" / "cloud_architecture_specification.pdf"
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.")
        sys.exit(1)

    print(f"Seeding database with benchmark document: {pdf_path.name}...")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    doc_id, saved_path, extracted_pages = PDFService.save_and_extract_text(
        file_bytes=file_bytes,
        original_filename=pdf_path.name
    )

    chunker = ChunkingService()
    chunks = chunker.chunk_document(
        extracted_pages=extracted_pages,
        document_id=doc_id,
        filename=pdf_path.name
    )

    chunk_texts = [c["text"] for c in chunks]
    embeddings = embedding_service.embed_texts(chunk_texts)
    vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

    db.insert_document(
        document_id=doc_id,
        filename=pdf_path.name,
        pages_processed=len(extracted_pages),
        chunks_created=len(chunks),
        file_size_bytes=len(file_bytes)
    )

    print(f"Seeding complete! Indexed {len(chunks)} chunks into vector store and SQLite.")


if __name__ == "__main__":
    seed()
