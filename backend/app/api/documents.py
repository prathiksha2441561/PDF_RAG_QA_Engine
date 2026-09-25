from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.app.config import settings
from backend.app.logger import logger
from backend.app.models.database import db
from backend.app.schemas.document import DocumentUploadResponse, DocumentInfo, DocumentListResponse
from backend.app.services.pdf_service import PDFService, PDFProcessingError
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.embedding_service import embedding_service
from backend.app.services.vector_store import vector_store

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF document"
)
async def upload_document(file: UploadFile = File(...)):
    """
    Ingests a PDF document:
    1. Validates file format and size limits
    2. Extracts text page-by-page preserving page numbers
    3. Breaks text into boundary-aware chunks with overlap
    4. Computes semantic embeddings
    5. Stores chunk vectors and metadata in vector store & SQLite
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    # Read binary content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file stream."
        )

    # Validate and extract text
    try:
        doc_id, saved_path, extracted_pages = PDFService.save_and_extract_text(
            file_bytes=content,
            original_filename=file.filename
        )
    except PDFProcessingError as pe:
        logger.warning(f"PDF Validation/Extraction Error: {str(pe)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(pe)
        )
    except Exception as e:
        logger.error(f"Unexpected error while extracting text: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the PDF file."
        )

    # Chunk the extracted pages
    chunker = ChunkingService()
    chunks = chunker.chunk_document(
        extracted_pages=extracted_pages,
        document_id=doc_id,
        filename=file.filename
    )

    # Generate embeddings and store
    if chunks:
        chunk_texts = [c["text"] for c in chunks]
        try:
            embeddings = embedding_service.embed_texts(chunk_texts)
            vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
        except Exception as e:
            logger.error(f"Failed generating or storing embeddings: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embeddings and index document in vector store."
            )

    # Persist metadata to SQLite
    doc_record = db.insert_document(
        document_id=doc_id,
        filename=file.filename,
        pages_processed=len(extracted_pages),
        chunks_created=len(chunks),
        file_size_bytes=len(content)
    )

    # Check if document appears to be a scanned image with minimal text
    total_text_chars = sum(p["char_count"] for p in extracted_pages)
    scan_warning = None
    if total_text_chars < 150:
        scan_warning = (
            "Notice: This PDF appears to be a scanned photo or image without an embedded digital text layer. "
            "Only URL metadata was extracted. An OCR engine (e.g. Tesseract) is required to parse text from scanned images."
        )
        logger.warning(f"Uploaded file '{file.filename}' has minimal extractable text ({total_text_chars} chars).")

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        pages_processed=len(extracted_pages),
        chunks_created=len(chunks),
        file_size_bytes=len(content),
        created_at=doc_record["uploaded_at"],
        warning=scan_warning
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents"
)
async def list_documents():
    """Returns a list of all indexed PDF documents with their metadata."""
    docs = db.list_documents()
    items = [
        DocumentInfo(
            document_id=d["document_id"],
            filename=d["filename"],
            pages_processed=d["pages_processed"],
            chunks_created=d["chunks_created"],
            file_size_bytes=d["file_size_bytes"],
            uploaded_at=d["uploaded_at"]
        )
        for d in docs
    ]
    return DocumentListResponse(total_documents=len(items), documents=items)
