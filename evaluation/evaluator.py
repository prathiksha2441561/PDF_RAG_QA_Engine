import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.services.evaluation_service import evaluation_service
from backend.app.config import settings


async def main():
    print("=" * 65)
    print(" RAG BENCHMARK EVALUATION RUNNER")
    print(f" LLM Provider: {settings.LLM_PROVIDER} | Embedding: {settings.EMBEDDING_MODEL}")
    print("=" * 65)

    try:
        report = await evaluation_service.run_evaluation()
    except Exception as e:
        print(f"ERROR: Failed to run evaluation: {str(e)}")
        sys.exit(1)

    print("\n" + "=" * 65)
    print(" EVALUATION RESULTS SUMMARY")
    print("=" * 65)
    print(f" Total Questions:        {report.total_questions}")
    print(f" Correct Answers:        {report.correct_answers}")
    print(f" Incorrect Answers:      {report.incorrect_answers}")
    print(f" Accuracy:               {report.accuracy_percent}%")
    print(f" Retrieval Hit Rate:     {report.retrieval_hit_rate_percent}%")
    print(f" Average Total Latency:  {report.average_latency_ms} ms")
    print("=" * 65)

    print("\nDetailed Question Breakdown:")
    for res in report.results:
        status_symbol = "[PASS]" if res.answer_correct else "[FAIL]"
        ret_symbol = "HIT" if res.retrieval_success else "MISS"
        print(f"\n{status_symbol} {res.id}: {res.question}")
        print(f"   Retrieval: {ret_symbol} | Groundedness: {res.groundedness} | Latency: {res.latency_ms}ms")
        print(f"   Expected:  {res.expected_answer}")
        print(f"   Generated: {res.generated_answer}")
        if res.retrieved_sources:
            src_str = ", ".join(f"{s.document}:p{s.page}" for s in res.retrieved_sources)
            print(f"   Sources:   {src_str}")
        if res.notes:
            print(f"   Notes:     {res.notes}")

    print("\n" + "=" * 65)
    print(f" Full JSON report saved to: evaluation/results/eval_report.json")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
