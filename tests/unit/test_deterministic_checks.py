"""Unit tests for deterministic quality checks (Layer 2)."""

import pytest

from src.evaluation.deterministic import run_deterministic_checks


def _make_lesson(**overrides):
    """Helper to build a lesson for deterministic testing."""
    lesson = {
        "title": "Introduction to RAG",
        "what_you_will_learn": ["What RAG is", "How retrieval works"],
        "sections": [
            {
                "heading": "Introduction",
                "content": (
                    "RAG stands for Retrieval-Augmented Generation. "
                    "It is a technique that retrieves information from a knowledge base. "
                    "Embeddings are numerical representations of text, like GPS coordinates for meaning. "
                    "A vector database stores these embeddings for fast search. "
                    "The retrieved context is provided to the LLM for generation. "
                    "For example, imagine you are searching for a recipe. "
                    "Think of it as looking up a book before answering. "
                ) * 10,
                "order": 0,
            },
        ] * 8,
        "quiz": [
            {"question": "Q?", "options": ["A", "B", "C", "D"],
             "correct_option_index": 0, "explanation": "E"}
        ] * 3,
        "summary": "RAG combines retrieval with generation. " * 5,
    }
    lesson.update(overrides)
    return lesson


class TestDeterministicChecks:
    """Tests for rule-based quality checks."""

    def test_valid_lesson_passes_most_checks(self):
        results = run_deterministic_checks(_make_lesson())
        critical_failures = [r for r in results if not r.passed and r.severity == "critical"]
        assert len(critical_failures) == 0, f"Critical failures: {[(r.check_name, r.message) for r in critical_failures]}"

    def test_prohibited_claim_detected(self):
        """The 'RAG retrains' prohibited claim must be caught."""
        lesson = _make_lesson()
        lesson["sections"][0]["content"] += " RAG retrains the LLM whenever new documents are added."
        results = run_deterministic_checks(lesson)
        prohibited = next((r for r in results if r.check_name == "prohibited_claims"), None)
        assert prohibited is not None
        assert not prohibited.passed
        assert prohibited.severity == "critical"

    def test_missing_concept_detected(self):
        """Missing required concepts should fail."""
        lesson = _make_lesson()
        # Replace content with text that doesn't mention required concepts
        for s in lesson["sections"]:
            s["content"] = "This is a simple lesson about technology. " * 50
        results = run_deterministic_checks(lesson)
        concept_check = next((r for r in results if r.check_name == "required_concepts"), None)
        assert concept_check is not None
        assert not concept_check.passed

    def test_concrete_example_required(self):
        """Lessons without examples should fail."""
        lesson = _make_lesson()
        for s in lesson["sections"]:
            s["content"] = (
                "RAG retrieves documents. Embeddings represent text as vectors. "
                "Vector databases store embeddings. Context is provided to the LLM for generation. "
            ) * 15
        results = run_deterministic_checks(lesson)
        example_check = next((r for r in results if r.check_name == "concrete_example"), None)
        assert example_check is not None
        assert not example_check.passed

    def test_word_count_too_short(self):
        """Very short lessons should fail min word count."""
        lesson = _make_lesson()
        for s in lesson["sections"]:
            s["content"] = "Short. "
        results = run_deterministic_checks(lesson)
        wc_check = next((r for r in results if r.check_name == "min_word_count"), None)
        assert wc_check is not None
        assert not wc_check.passed


class TestGateLogic:
    """Tests for the deterministic pass/fail gate."""

    def test_all_pass_returns_true(self):
        from src.evaluation.gate import evaluate_gate
        from src.graph.state import ValidationResult, GroundingResult, SemanticCheckResult

        val = [ValidationResult(check_name="test", passed=True, severity="critical", message="ok")]
        grnd = [GroundingResult(claim="test", supported=True, severity="critical", reason="ok")]
        sem = [
            SemanticCheckResult(dimension=d, passed=True, severity="critical", reason="ok")
            for d in ["accuracy", "grounding", "beginner_friendliness", "jargon_handling",
                       "coverage", "teaching_by_example", "coherence", "clarity"]
        ]
        result = evaluate_gate(val, grnd, sem)
        assert result.overall_passed

    def test_critical_failure_returns_false(self):
        from src.evaluation.gate import evaluate_gate
        from src.graph.state import ValidationResult, GroundingResult, SemanticCheckResult

        val = [ValidationResult(check_name="test", passed=False, severity="critical", message="fail")]
        result = evaluate_gate(val, [], [])
        assert not result.overall_passed
        assert len(result.critical_failures) > 0

    def test_missing_dimension_returns_false(self):
        from src.evaluation.gate import evaluate_gate
        from src.graph.state import SemanticCheckResult

        # Only 3 dimensions — missing the rest
        sem = [
            SemanticCheckResult(dimension=d, passed=True, severity="critical", reason="ok")
            for d in ["accuracy", "grounding", "clarity"]
        ]
        result = evaluate_gate([], [], sem)
        assert not result.overall_passed
