"""Unit tests for structural validation (Layer 1)."""

import pytest

from src.evaluation.structural import validate_lesson_structure


def _make_valid_lesson(**overrides):
    """Helper to build a valid lesson with optional overrides."""
    lesson = {
        "title": "Introduction to RAG",
        "what_you_will_learn": ["What RAG is", "How RAG works", "Why RAG matters"],
        "sections": [
            {"heading": f"Section {i}", "content": f"Content for section {i}. " * 20, "order": i}
            for i in range(10)
        ],
        "quiz": [
            {
                "question": f"Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_option_index": 0,
                "explanation": f"Explanation {i}",
            }
            for i in range(3)
        ],
        "summary": "RAG is a powerful technique that combines information retrieval with text generation. " * 3,
    }
    lesson.update(overrides)
    return lesson


class TestStructuralValidation:
    """Tests for Pydantic-based structural validation."""

    def test_valid_lesson_passes(self):
        results = validate_lesson_structure(_make_valid_lesson())
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0, f"Unexpected failures: {[(r.check_name, r.message) for r in failed]}"

    def test_empty_title_fails(self):
        results = validate_lesson_structure(_make_valid_lesson(title=""))
        title_check = next(r for r in results if r.check_name == "non_empty_title")
        assert not title_check.passed
        assert title_check.severity == "critical"

    def test_too_few_sections_fails(self):
        results = validate_lesson_structure(_make_valid_lesson(
            sections=[{"heading": "Only", "content": "Content " * 20, "order": 0}]
        ))
        check = next(r for r in results if r.check_name == "minimum_sections")
        assert not check.passed

    def test_empty_section_fails(self):
        sections = [{"heading": f"S{i}", "content": "Content " * 20, "order": i} for i in range(10)]
        sections[3]["content"] = ""
        results = validate_lesson_structure(_make_valid_lesson(sections=sections))
        check = next(r for r in results if r.check_name == "non_empty_sections")
        assert not check.passed

    def test_quiz_too_few_fails(self):
        results = validate_lesson_structure(_make_valid_lesson(
            quiz=[{"question": "Q?", "options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "E"}]
        ))
        check = next(r for r in results if r.check_name == "quiz_minimum_questions")
        assert not check.passed

    def test_invalid_schema_fails(self):
        results = validate_lesson_structure({"not": "a lesson"})
        check = next(r for r in results if r.check_name == "pydantic_parse")
        assert not check.passed
        assert check.severity == "critical"
