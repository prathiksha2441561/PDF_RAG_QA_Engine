from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.evaluation import EvalReportResponse
from backend.app.services.evaluation_service import evaluation_service
from backend.app.logger import logger

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])


@router.post(
    "",
    response_model=EvalReportResponse,
    summary="Run automated 10-question evaluation benchmark"
)
async def run_evaluation():
    """
    Executes the 10-question RAG evaluation benchmark:
    - Tests direct factual, comparison, numerical, and out-of-context queries
    - Measures retrieval hit rate, answer correctness, and latency
    - Saves evaluation report to disk and returns full structured metrics
    """
    try:
        report = await evaluation_service.run_evaluation()
        return report
    except FileNotFoundError as fe:
        logger.error(f"Questions configuration missing: {str(fe)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(fe)
        )
    except Exception as e:
        logger.error(f"Evaluation benchmark failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete the evaluation benchmark run."
        )


@router.get(
    "/questions",
    summary="Get predefined evaluation questions"
)
async def get_evaluation_questions():
    """Returns the list of 10 test questions configured for evaluation."""
    try:
        questions = evaluation_service.load_questions()
        return [q.model_dump() for q in questions]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load evaluation questions: {str(e)}"
        )
