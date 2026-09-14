"""Rubric definitions and versioning.

Centralizes the evaluation rubric so it can be versioned,
tested, and evolved through the self-evolution pipeline.
"""

from typing import Any


RUBRIC_VERSION = "1.0.0"

RUBRIC_DIMENSIONS = [
    {
        "name": "accuracy",
        "description": "All technical explanations must be factually correct",
        "severity": "critical",
        "pass_criteria": "Zero factually incorrect statements about core concepts",
        "fail_examples": [
            "RAG retrains the LLM",
            "RAG modifies model weights",
            "Embeddings are keyword searches",
        ],
    },
    {
        "name": "grounding",
        "description": "Claims must be supported by knowledge base evidence",
        "severity": "critical",
        "pass_criteria": "All core claims have KB evidence support",
        "fail_examples": [
            "Making claims not in the knowledge base",
            "Contradicting knowledge base content",
        ],
    },
    {
        "name": "beginner_friendliness",
        "description": "Suitable for 12th-grade, limited-English learner from India",
        "severity": "critical",
        "pass_criteria": "No assumed prior ML/AI knowledge; simple language throughout",
        "fail_examples": [
            "Assuming knowledge of neural networks",
            "Using academic English",
            "Complex mathematical notation",
        ],
    },
    {
        "name": "jargon_handling",
        "description": "Every technical term explained before or at first use",
        "severity": "critical",
        "pass_criteria": "All jargon terms are defined in context",
        "fail_examples": [
            "Using 'embeddings' without explanation",
            "Mentioning 'HNSW' without context",
            "Referencing 'cosine similarity' cold",
        ],
    },
    {
        "name": "coverage",
        "description": "All required RAG concepts covered",
        "severity": "critical",
        "pass_criteria": "Retrieval, embeddings, vector DB, context, generation, architecture all covered",
        "fail_examples": [
            "Missing vector database explanation",
            "No discussion of embeddings",
            "Skipping the generation step",
        ],
    },
    {
        "name": "teaching_by_example",
        "description": "At least one concrete, relatable, end-to-end example",
        "severity": "critical",
        "pass_criteria": "Contains a real-world scenario walking through the complete RAG pipeline",
        "fail_examples": [
            "Only abstract descriptions",
            "Example mentions RAG but doesn't walk through steps",
        ],
    },
    {
        "name": "coherence",
        "description": "Logical flow from simple to complex concepts",
        "severity": "major",
        "pass_criteria": "No conceptual jumps; each section builds on the previous",
        "fail_examples": [
            "Discussing vector DBs before explaining embeddings",
            "Jumping to architecture before explaining components",
        ],
    },
    {
        "name": "clarity",
        "description": "Short sentences, simple words, active voice",
        "severity": "major",
        "pass_criteria": "Average sentence length ≤ 20 words; active voice preferred",
        "fail_examples": [
            "Long, compound sentences",
            "Passive voice throughout",
            "Ambiguous pronoun references",
        ],
    },
]

REQUIRED_SECTIONS = [
    "Title",
    "What You Will Learn",
    "Simple Introduction",
    "The Problem Before RAG",
    "What RAG Means",
    "Why RAG is Useful",
    "How RAG Works",
    "Step-by-Step Explanation",
    "Simple Real-World Example",
    "RAG Architecture",
    "RAG vs Normal LLM",
    "Common Misconceptions",
    "Mini Quiz",
    "Summary",
]


def get_rubric() -> dict[str, Any]:
    """Get the current rubric as a dictionary."""
    return {
        "version": RUBRIC_VERSION,
        "dimensions": RUBRIC_DIMENSIONS,
        "required_sections": REQUIRED_SECTIONS,
        "pass_policy": "ALL critical dimensions must pass. No partial credit.",
        "retry_policy": "Maximum 2 retries. Retry limit enforced by application code.",
    }
