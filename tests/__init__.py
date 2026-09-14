"""Unit tests for structural validation (Layer 1)."""

import pytest

from src.evaluation.structural import validate_lesson_structure


class TestStructuralValidation:
    """Tests for Pydantic-based structural validation."""

    def test_valid_lesson_passes(self):
        """A well-formed lesson should pass structural validation."""
        lesson = {
            "title": "Introduction to RAG",
            "what_you_will_learn": ["What RAG is", "How RAG works", "Why RAG matters"],
            "sections": [
                {"heading": f"Section {i}", "content": f"Content for section {i} " * 20, "order": i}
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
            "summary": "RAG is a technique that combines retrieval with generation to produce better, more accurate responses. " * 3,
        }
        results = validate_lesson_structure(lesson)
        assert all(r.passed for r in results), f"Failed checks: {[r for r in results if not r.passed]}"

    def test_empty_title_fails(self):
        """An empty title should be a critical failure."""
        lesson = {
            "title": "",
            "what_you_will_learn": ["Something"],
            "sections": [{"heading": f"S{i}", "content": "Content " * 20, "order": i} for i in range(10)],
            "quiz": [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "E"}] * 3,
            "summary": "Summary text " * 10,
        }
        results = validate_lesson_structure(lesson)
        title_check = next(r for r in results if r.check_name == "non_empty_title")
        assert not title_check.passed
        assert title_check.severity == "critical"

    def test_too_few_sections_fails(self):
        """Fewer than 8 sections should fail."""
        lesson = {
            "title": "Introduction to RAG",
            "what_you_will_learn": ["Something"],
            "sections": [{"heading": "Only One", "content": "Content " * 20, "order": 0}],
            "quiz": [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "E"}] * 3,
            "summary": "Summary text " * 10,
        }
        results = validate_lesson_structure(lesson)
        section_check = next(r for r in results if r.check_name == "minimum_sections")
        assert not section_check.passed

    def test_empty_section_content_fails(self):
        """Sections with empty content should fail."""
        lesson = {
            "title": "Introduction to RAG",
            "what_you_will_learn": ["Something"],
            "sections": [
                {"heading": f"Section {i}", "content": "Content " * 20 if i != 3 else "", "order": i}
                for i in range(10)
            ],
            "quiz": [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "E"}] * 3,
            "summary": "Summary text " * 10,
        }
        results = validate_lesson_structure(lesson)
        content_check = next(r for r in results if r.check_name == "non_empty_sections")
        assert not content_check.passed

    def test_too_few_quiz_questions_fails(self):
        """Fewer than 3 quiz questions should fail."""
        lesson = {
            "title": "Introduction to RAG",
            "what_you_will_learn": ["Something"],
            "sections": [{"heading": f"S{i}", "content": "Content " * 20, "order": i} for i in range(10)],
            "quiz": [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "E"}],
            "summary": "Summary text " * 10,
        }
        results = validate_lesson_structure(lesson)
        quiz_check = next(r for r in results if r.check_name == "quiz_minimum_questions")
        assert not quiz_check.passed

    def test_invalid_schema_fails(self):
        """Invalid schema should fail at parse level."""
        results = validate_lesson_structure({"bad": "data"})
        assert any(not r.passed and r.check_name == "pydantic_parse" for r in results)
