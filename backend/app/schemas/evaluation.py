from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.query import SourceReference


class EvalQuestion(BaseModel):
    id: str
    question: str
    expected_answer: str
    category: Optional[str] = "factual"
    source: Optional[Dict[str, Any]] = None


class EvalItemResult(BaseModel):
    id: str
    question: str
    expected_answer: str
    generated_answer: str
    retrieved_sources: List[SourceReference]
    retrieval_success: bool
    answer_correct: bool
    groundedness: str  # "GROUNDED", "UNGROUNDED", "OUT_OF_CONTEXT_HANDLED"
    latency_ms: float
    notes: Optional[str] = None


class EvalReportResponse(BaseModel):
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    accuracy_percent: float
    retrieval_hit_rate_percent: float
    average_latency_ms: float
    results: List[EvalItemResult]
    timestamp: str
