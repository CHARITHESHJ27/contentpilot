"""Tests for self-evolution pipeline and rejection log diff computation."""

import pytest
from src.api.routes import _compute_rejection_diff
from src.memory.self_evolution import SelfEvolutionPipeline


def test_compute_rejection_diff_single_attempt():
    """Diff requires at least 2 attempts."""
    lesson_versions = [{"version": 1, "lesson": {"sections": []}}]
    diff = _compute_rejection_diff(lesson_versions)
    assert diff == []


def test_compute_rejection_diff_deliberate_failure_detected():
    """Detects false claim from attempt 1 and shows corrected claim in attempt 2."""
    lesson_versions = [
        {
            "version": 1,
            "lesson": {
                "sections": [
                    {"heading": "HOW It Works", "content": "RAG retrains the LLM whenever new documents are added to the vector index."}
                ]
            },
        },
        {
            "version": 2,
            "lesson": {
                "sections": [
                    {"heading": "HOW It Works", "content": "RAG retrieves external chunks at inference time without retraining the LLM weights."}
                ]
            },
        },
    ]

    diff = _compute_rejection_diff(lesson_versions)
    assert len(diff) >= 1
    accuracy_diff = next((d for d in diff if "Accuracy" in d["dimension"]), None)
    assert accuracy_diff is not None
    assert "retrains" in accuracy_diff["before"]
    assert "inference" in accuracy_diff["after"]


def test_compute_rejection_diff_section_change():
    """Detects when section contents are improved between attempts."""
    lesson_versions = [
        {
            "version": 1,
            "lesson": {
                "sections": [
                    {"heading": "WHAT is RAG", "content": "Short definition without Indian context."}
                ]
            },
        },
        {
            "version": 2,
            "lesson": {
                "sections": [
                    {"heading": "WHAT is RAG", "content": "Expanded definition using a cricket scorebook analogy for 12th grade learners."}
                ]
            },
        },
    ]

    diff = _compute_rejection_diff(lesson_versions)
    assert len(diff) >= 1
    section_diff = next((d for d in diff if "WHAT is RAG" in d["dimension"]), None)
    assert section_diff is not None
    assert "Short definition" in section_diff["before"]
    assert "Expanded definition" in section_diff["after"]
