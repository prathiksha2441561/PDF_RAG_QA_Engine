import time
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.query import QueryRequest, QueryResponse
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.llm_service import llm_service
from backend.app.models.database import db
from backend.app.logger import logger

router = APIRouter(tags=["Query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question against indexed documents"
)
async def query_documents(request: QueryRequest):
    """
    RAG Query Endpoint:
    1. Validates user input and scans for security threats.
    2. Retrieves top-k semantically relevant chunks from vector store.
    3. Prompts the configured LLM using strict grounding guardrails.
    4. Enforces data-leakage sanitization on the model response.
    5. Returns answer along with exact document and page source references.
    """
    clean_question = request.question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or blank."
        )

    start_total = time.perf_counter()

    # 1. Retrieve relevant chunks
    try:
        raw_chunks, sources, retrieval_latency_ms = retrieval_service.retrieve(
            query=clean_question,
            top_k=request.top_k,
            document_id=request.document_id
        )
    except Exception as e:
        logger.error(f"Error during chunk retrieval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve relevant document context."
        )

    # 2. Generate grounded answer via LLM
    try:
        answer, final_sources, gen_latency_ms, is_flagged, flag_note = await llm_service.generate_answer(
            question=clean_question,
            retrieved_chunks=raw_chunks,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Error during LLM generation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the answer."
        )

    total_latency_ms = round((time.perf_counter() - start_total) * 1000, 2)

    # 3. Log query to database for audit & observability
    db.log_query(
        question=clean_question,
        latency_ms=total_latency_ms,
        sources_count=len(final_sources),
        security_flagged=is_flagged,
        security_note=flag_note
    )

    return QueryResponse(
        question=clean_question,
        answer=answer,
        sources=final_sources,
        latency_ms=total_latency_ms,
        security_flagged=is_flagged,
        security_note=flag_note
    )
