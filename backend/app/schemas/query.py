from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language question to ask against the uploaded documents"
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of relevant chunks to retrieve (defaults to server config if omitted)"
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Optional document ID to restrict search scope to a single document"
    )


class SourceReference(BaseModel):
    document: str = Field(..., description="Document filename")
    document_id: str = Field(..., description="Document unique ID")
    page: int = Field(..., description="1-indexed page number in the original PDF")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    relevance_score: Optional[float] = Field(default=None, description="Similarity score or distance metric")
    snippet: Optional[str] = Field(default=None, description="Preview snippet of the chunk text")


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceReference]
    latency_ms: float
    security_flagged: bool = False
    security_note: Optional[str] = None
