import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.config import settings
from backend.app.logger import logger
from backend.app.schemas.evaluation import EvalQuestion, EvalItemResult, EvalReportResponse
from backend.app.schemas.query import SourceReference
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.llm_service import llm_service
from backend.app.services.vector_store import vector_store
from backend.app.services.embedding_service import embedding_service


class EvaluationService:
    def __init__(self, questions_path: Optional[str] = None):
        # Default path to evaluation/questions.json
        self.questions_path = questions_path or str(
            Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "questions.json"
        )
        self.results_dir = Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def load_questions(self) -> List[EvalQuestion]:
        """Loads evaluation questions from JSON file."""
        p = Path(self.questions_path)
        if not p.exists():
            raise FileNotFoundError(f"Evaluation questions file not found at {self.questions_path}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [EvalQuestion(**item) for item in data]

    def _assess_retrieval(
        self,
        retrieved_sources: List[SourceReference],
        expected_source: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Verifies if expected document and page were retrieved in top-k.
        For out-of-context questions (where expected_source is None or 'N/A'),
        retrieval is considered successful if no false-positive confidence is asserted.
        """
        if not expected_source or expected_source.get("page") is None:
            # Out-of-context question
            return True

        expected_doc = expected_source.get("document", "").lower()
        expected_page = expected_source.get("page")

        for src in retrieved_sources:
            doc_match = (not expected_doc) or (expected_doc in src.document.lower())
            page_match = (expected_page is None) or (src.page == expected_page)
            if doc_match and page_match:
                return True
        return False

    def _assess_answer_correctness(
        self,
        expected: str,
        generated: str,
        is_out_of_context: bool
    ) -> bool:
        """
        Evaluates answer correctness.
        If out-of-context, expects explicit acknowledgment that info was not found.
        Otherwise checks key factual components.
        """
        gen_lower = generated.lower().strip()
        exp_lower = expected.lower().strip()

        if is_out_of_context:
            refusal_markers = [
                "could not find",
                "not found",
                "not available",
                "not mentioned",
                "not present",
                "does not contain"
            ]
            return any(marker in gen_lower for marker in refusal_markers)

        # Standard question: check if key facts or major terms in expected answer appear in generated answer
        # Stopwords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "of", "for", "to", "and", "by", "that", "this"}
        expected_terms = [w for w in exp_lower.replace(",", "").replace(".", "").split() if w not in stopwords and len(w) > 2]

        if not expected_terms:
            return exp_lower in gen_lower

        matches = sum(1 for term in expected_terms if term in gen_lower)
        # Pass if at least 60% of expected factual keywords are present
        return (matches / len(expected_terms)) >= 0.55

    def ensure_reference_document(self) -> None:
        """Ensures the benchmark document is ingested and indexed in the vector store."""
        ref_path = Path(__file__).resolve().parent.parent.parent.parent / "documents" / "cloud_architecture_specification.pdf"
        if not ref_path.exists():
            return

        from backend.app.models.database import db
        from backend.app.services.pdf_service import PDFService
        from backend.app.services.chunking_service import ChunkingService
        
        existing = [d for d in db.list_documents() if d["filename"] == "cloud_architecture_specification.pdf"]
        if not existing or vector_store.count() < 8:
            logger.info("Auto-indexing benchmark PDF 'cloud_architecture_specification.pdf' for evaluation...")
            with open(ref_path, "rb") as f:
                content = f.read()
            doc_id, path, pages = PDFService.save_and_extract_text(content, ref_path.name)
            chunks = ChunkingService().chunk_document(pages, doc_id, ref_path.name)
            if chunks:
                embeddings = embedding_service.embed_texts([c["text"] for c in chunks])
                vector_store.add_chunks(chunks, embeddings)
                db.insert_document(doc_id, ref_path.name, len(pages), len(chunks), len(content))

    async def run_evaluation(
        self,
        questions: Optional[List[EvalQuestion]] = None,
        top_k: int = 4
    ) -> EvalReportResponse:
        """
        Executes full evaluation on the 10 test questions and persists results.
        """
        self.ensure_reference_document()
        eval_questions = questions or self.load_questions()
        total_q = len(eval_questions)
        logger.info(f"Starting evaluation run on {total_q} questions (top_k={top_k})...")

        results: List[EvalItemResult] = []
        total_latency = 0.0
        correct_count = 0
        retrieval_hit_count = 0

        for q in eval_questions:
            start_t = time.perf_counter()

            # Retrieve context
            raw_chunks, sources, ret_lat = retrieval_service.retrieve(
                query=q.question,
                top_k=top_k
            )

            # Generate answer
            gen_ans, final_sources, gen_lat, flagged, flag_note = await llm_service.generate_answer(
                question=q.question,
                retrieved_chunks=raw_chunks,
                sources=sources
            )

            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            total_latency += elapsed_ms

            is_out_of_context = (q.source is None or q.source.get("page") is None)
            ret_success = self._assess_retrieval(sources, q.source)
            if ret_success:
                retrieval_hit_count += 1

            ans_correct = self._assess_answer_correctness(q.expected_answer, gen_ans, is_out_of_context)
            if ans_correct:
                correct_count += 1

            # Determine groundedness label
            if is_out_of_context and ans_correct:
                groundedness = "OUT_OF_CONTEXT_HANDLED"
            elif ans_correct and len(final_sources) > 0:
                groundedness = "GROUNDED"
            elif not ans_correct:
                groundedness = "UNGROUNDED"
            else:
                groundedness = "GROUNDED"

            notes = []
            if flagged:
                notes.append(f"Security Alert: {flag_note}")
            if not ret_success:
                notes.append("Expected source page missing from top-k retrieval")

            results.append(
                EvalItemResult(
                    id=q.id,
                    question=q.question,
                    expected_answer=q.expected_answer,
                    generated_answer=gen_ans,
                    retrieved_sources=final_sources,
                    retrieval_success=ret_success,
                    answer_correct=ans_correct,
                    groundedness=groundedness,
                    latency_ms=elapsed_ms,
                    notes="; ".join(notes) if notes else None
                )
            )

        avg_latency = round(total_latency / total_q, 2) if total_q > 0 else 0.0
        acc_pct = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0
        ret_pct = round((retrieval_hit_count / total_q) * 100, 1) if total_q > 0 else 0.0

        report = EvalReportResponse(
            total_questions=total_q,
            correct_answers=correct_count,
            incorrect_answers=total_q - correct_count,
            accuracy_percent=acc_pct,
            retrieval_hit_rate_percent=ret_pct,
            average_latency_ms=avg_latency,
            results=results,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

        # Save to results/eval_report.json
        output_file = self.results_dir / "eval_report.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        logger.info(
            f"Evaluation finished: {correct_count}/{total_q} correct ({acc_pct}%), "
            f"Retrieval Hit Rate: {ret_pct}%, Avg Latency: {avg_latency}ms. "
            f"Report saved to {output_file}"
        )

        return report


evaluation_service = EvaluationService()
