import pytest
from backend.app.services.evaluation_service import evaluation_service


def test_evaluation_questions_count_and_structure():
    questions = evaluation_service.load_questions()
    assert len(questions) == 10, f"Expected exactly 10 evaluation questions, got {len(questions)}"

    categories = set()
    has_out_of_context = False

    for q in questions:
        assert q.id is not None
        assert len(q.question) > 5
        assert len(q.expected_answer) > 5
        if q.category:
            categories.add(q.category)
        if q.category in ("out_of_context", "hallucination_probe") or q.source.get("page") is None:
            has_out_of_context = True

    assert has_out_of_context is True, "Must include at least one out-of-context question test"
    assert len(categories) >= 3, "Evaluation suite must cover diverse question categories"


@pytest.mark.asyncio
async def test_run_evaluation_pipeline():
    report = await evaluation_service.run_evaluation(top_k=4)
    assert report.total_questions == 10
    assert report.correct_answers >= 8, f"Expected at least 8/10, got {report.correct_answers}"
    assert report.accuracy_percent >= 80.0
    assert report.retrieval_hit_rate_percent >= 80.0
    assert report.average_latency_ms > 0
    assert len(report.results) == 10
