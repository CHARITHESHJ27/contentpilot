"""Layer 2 — Deterministic quality checks.

Rule-based checks that do NOT require an LLM.
Checks that can be deterministic SHOULD be deterministic —
cheaper, faster, and more reliable than LLM evaluation.
"""

import re
from typing import Any

from src.graph.state import GeneratedLesson, ValidationResult
from src.observability import get_logger

logger = get_logger(__name__)

# Known jargon terms that must be explained
JARGON_TERMS = {
    "embedding", "embeddings", "vector", "vectors", "vector database",
    "cosine similarity", "semantic search", "transformer", "neural network",
    "token", "tokens", "tokenization", "context window", "fine-tuning",
    "fine-tune", "inference", "latent", "latency", "api", "llm",
    "large language model", "natural language processing", "nlp",
    "deep learning", "machine learning", "model weights", "parameters",
    "prompt engineering", "hallucination", "grounding", "retrieval-augmented",
    "indexing", "chunking", "reranking", "cross-encoder", "dense retrieval",
    "sparse retrieval", "hnsw",
}

# Prohibited claims that should NEVER appear
PROHIBITED_PATTERNS = [
    r"rag\s+retrain",
    r"rag\s+retrains",
    r"rag\s+fine[\s-]?tunes?\s+the\s+(llm|model)",
    r"rag\s+modifies?\s+(the\s+)?(llm|model)\s*(weights|parameters)",
    r"rag\s+updates?\s+the\s+(llm|model)",
    r"retrains?\s+the\s+(llm|model)\s+whenever",
]

# Required concepts that must appear
REQUIRED_CONCEPTS = [
    "retrieval",
    "embedding",
    "vector",
    "context",
    "generation",
]


def _get_full_text(lesson: GeneratedLesson) -> str:
    """Get the complete lesson text for analysis."""
    parts = [lesson.title]
    parts.extend(lesson.what_you_will_learn)
    for section in lesson.sections:
        parts.append(section.heading)
        parts.append(section.content)
    parts.append(lesson.summary)
    return "\n".join(parts)


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _average_sentence_length(text: str) -> float:
    """Calculate average sentence length in words."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _calculate_jargon_density(text: str) -> tuple[float, list[str]]:
    """Calculate the ratio of jargon terms to total words.

    Returns (density, list of found jargon terms).
    """
    words = text.lower().split()
    total_words = len(words)
    if total_words == 0:
        return 0.0, []

    found_jargon = set()
    text_lower = text.lower()
    for term in JARGON_TERMS:
        if term in text_lower:
            found_jargon.add(term)

    # Count jargon word occurrences
    jargon_word_count = 0
    for term in found_jargon:
        jargon_word_count += text_lower.count(term)

    density = jargon_word_count / total_words if total_words > 0 else 0.0
    return density, sorted(found_jargon)


def _check_jargon_explained(text: str, jargon_terms: list[str]) -> list[str]:
    """Check if jargon terms are explained within ±2 sentences of first use.

    Returns list of unexplained jargon terms.
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    unexplained = []

    explanation_indicators = [
        "means", "refers to", "is a", "is an", "are called", "which is",
        "in simple terms", "basically", "think of it as", "like a",
        "for example", "such as", "also known as", "that is",
        "in other words", "simply put", "is when", "is the process",
    ]

    for term in jargon_terms:
        term_lower = term.lower()
        first_use_idx = None

        for idx, sentence in enumerate(sentences):
            if term_lower in sentence.lower():
                first_use_idx = idx
                break

        if first_use_idx is None:
            continue

        # Check ±2 sentences for explanation
        start = max(0, first_use_idx - 2)
        end = min(len(sentences), first_use_idx + 3)
        context_window = " ".join(sentences[start:end]).lower()

        is_explained = any(indicator in context_window for indicator in explanation_indicators)

        if not is_explained:
            unexplained.append(term)

    return unexplained


def _check_duplicate_sections(lesson: GeneratedLesson) -> list[str]:
    """Find duplicate section headings."""
    headings = [s.heading.lower().strip() for s in lesson.sections]
    seen: set[str] = set()
    duplicates: list[str] = []
    for h in headings:
        if h in seen:
            duplicates.append(h)
        seen.add(h)
    return duplicates


def run_deterministic_checks(lesson_data: dict[str, Any]) -> list[ValidationResult]:
    """Run all deterministic quality checks on a lesson.

    These checks are rule-based and do not use an LLM.
    """
    results: list[ValidationResult] = []

    try:
        lesson = GeneratedLesson(**lesson_data)
    except Exception:
        results.append(ValidationResult(
            check_name="parse_for_deterministic",
            passed=False,
            severity="critical",
            message="Cannot parse lesson for deterministic checks",
        ))
        return results

    full_text = _get_full_text(lesson)
    word_count = _count_words(full_text)

    # Check 1: Minimum word count
    if word_count < 1500:
        results.append(ValidationResult(
            check_name="min_word_count",
            passed=False,
            severity="major",
            message=f"Lesson has {word_count} words, minimum 1500 required",
        ))
    else:
        results.append(ValidationResult(
            check_name="min_word_count",
            passed=True,
            severity="major",
            message=f"Word count: {word_count}",
        ))

    # Check 2: Maximum word count
    if word_count > 8000:
        results.append(ValidationResult(
            check_name="max_word_count",
            passed=False,
            severity="minor",
            message=f"Lesson has {word_count} words, maximum 8000 recommended",
        ))
    else:
        results.append(ValidationResult(
            check_name="max_word_count",
            passed=True,
            severity="minor",
            message=f"Word count within limits: {word_count}",
        ))

    # Check 3: Average sentence length
    avg_sentence_len = _average_sentence_length(full_text)
    if avg_sentence_len > 20:
        results.append(ValidationResult(
            check_name="sentence_complexity",
            passed=False,
            severity="major",
            message=f"Average sentence length is {avg_sentence_len:.1f} words (max 20)",
        ))
    else:
        results.append(ValidationResult(
            check_name="sentence_complexity",
            passed=True,
            severity="major",
            message=f"Average sentence length: {avg_sentence_len:.1f} words",
        ))

    # Check 4: Duplicate sections
    duplicates = _check_duplicate_sections(lesson)
    if duplicates:
        results.append(ValidationResult(
            check_name="duplicate_sections",
            passed=False,
            severity="major",
            message=f"Duplicate section headings: {', '.join(duplicates)}",
        ))
    else:
        results.append(ValidationResult(
            check_name="duplicate_sections",
            passed=True,
            severity="major",
            message="No duplicate sections",
        ))

    # Check 5: Jargon density
    jargon_density, found_jargon = _calculate_jargon_density(full_text)
    if jargon_density > 0.15:
        results.append(ValidationResult(
            check_name="jargon_density",
            passed=False,
            severity="major",
            message=f"Jargon density is {jargon_density:.1%} (max 15%)",
        ))
    else:
        results.append(ValidationResult(
            check_name="jargon_density",
            passed=True,
            severity="major",
            message=f"Jargon density: {jargon_density:.1%}",
        ))

    # Check 6: Jargon explanation
    unexplained = _check_jargon_explained(full_text, found_jargon)
    if unexplained:
        results.append(ValidationResult(
            check_name="jargon_explained",
            passed=False,
            severity="critical",
            message=f"Unexplained jargon terms: {', '.join(unexplained[:5])}",
        ))
    else:
        results.append(ValidationResult(
            check_name="jargon_explained",
            passed=True,
            severity="critical",
            message="All jargon terms appear to be explained",
        ))

    # Check 7: Required concepts present
    text_lower = full_text.lower()
    missing_concepts = [c for c in REQUIRED_CONCEPTS if c not in text_lower]
    if missing_concepts:
        results.append(ValidationResult(
            check_name="required_concepts",
            passed=False,
            severity="critical",
            message=f"Missing required concepts: {', '.join(missing_concepts)}",
        ))
    else:
        results.append(ValidationResult(
            check_name="required_concepts",
            passed=True,
            severity="critical",
            message="All required concepts are covered",
        ))

    # Check 8: Concrete example exists
    example_patterns = [
        r"for example", r"imagine", r"think of", r"let's say",
        r"consider", r"real.world", r"real-world", r"scenario",
        r"suppose", r"like when",
    ]
    has_example = any(
        re.search(pattern, text_lower) for pattern in example_patterns
    )
    if not has_example:
        results.append(ValidationResult(
            check_name="concrete_example",
            passed=False,
            severity="critical",
            message="No concrete example found in the lesson",
        ))
    else:
        results.append(ValidationResult(
            check_name="concrete_example",
            passed=True,
            severity="critical",
            message="Concrete example found",
        ))

    # Check 9: Prohibited claims
    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, text_lower):
            results.append(ValidationResult(
                check_name="prohibited_claims",
                passed=False,
                severity="critical",
                message=f"Prohibited claim found matching pattern: {pattern}",
            ))
            break
    else:
        results.append(ValidationResult(
            check_name="prohibited_claims",
            passed=True,
            severity="critical",
            message="No prohibited claims detected",
        ))

    # Check 10: Output size limit
    output_size = len(full_text.encode("utf-8"))
    if output_size > 32768:
        results.append(ValidationResult(
            check_name="output_size",
            passed=False,
            severity="minor",
            message=f"Output size is {output_size} bytes (max 32KB)",
        ))
    else:
        results.append(ValidationResult(
            check_name="output_size",
            passed=True,
            severity="minor",
            message=f"Output size: {output_size} bytes",
        ))

    logger.info(
        "deterministic_checks_completed",
        total_checks=len(results),
        passed=sum(1 for r in results if r.passed),
        failed=sum(1 for r in results if not r.passed),
    )

    return results
