from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str = Field(..., description="Unique UUID identifier for the uploaded document")
    filename: str = Field(..., description="Original name of the uploaded PDF file")
    pages_processed: int = Field(..., ge=0, description="Total number of pages extracted")
    chunks_created: int = Field(..., ge=0, description="Total number of text chunks generated and indexed")
    file_size_bytes: int = Field(..., ge=0, description="Size of the uploaded file in bytes")
    created_at: str = Field(..., description="ISO 8601 upload timestamp")
    warning: Optional[str] = Field(default=None, description="Warning if document appears to be a scanned image")


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    pages_processed: int
    chunks_created: int
    file_size_bytes: int
    uploaded_at: str


class DocumentListResponse(BaseModel):
    total_documents: int
    documents: List[DocumentInfo]
