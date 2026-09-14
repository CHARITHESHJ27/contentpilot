"""Layer 3 — Grounding evaluation.

Extracts factual claims from the lesson and verifies each
against the knowledge base. Catches hallucinations and
factual errors that deterministic checks can't detect.
"""

import json
from typing import Any

from src.graph.state import GeneratedLesson, GroundingResult
from src.llm.prompts import CLAIM_EXTRACTOR_PROMPT, GROUNDING_CHECK_PROMPT
from src.llm.provider import LLMProvider
from src.observability import get_logger
from src.observability.tracing import MetricsCollector
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.pgvector_client import PgVectorManager
from src.retrieval.pipeline import RetrievalPipeline

logger = get_logger(__name__)


async def extract_claims(lesson_text: str, llm: LLMProvider) -> list[str]:
    """Extract verifiable factual claims from a lesson using the LLM."""
    response = await llm.generate(
        system_prompt=CLAIM_EXTRACTOR_PROMPT,
        user_prompt=f"LESSON:\n{lesson_text}",
        node_name="extract_claims",
        temperature=0.1,
    )

    # Parse claims
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        claims = json.loads(cleaned)
        if isinstance(claims, list):
            return [str(c) for c in claims]
    except json.JSONDecodeError:
        # Fallback: split by newlines
        lines = [line.strip().strip("-•*") for line in response.split("\n")]
        return [line for line in lines if len(line) > 20]

    return []


async def check_claim_grounding(
    claim: str,
    evidence_text: str,
    source: str,
    llm: LLMProvider,
) -> GroundingResult:
    """Check whether a claim is supported by knowledge base evidence."""
    prompt = GROUNDING_CHECK_PROMPT.format(
        claim=claim,
        evidence=evidence_text,
    )

    response = await llm.generate(
        system_prompt="You are a strict fact-checker. Return JSON only.",
        user_prompt=prompt,
        node_name="grounding_check",
        temperature=0.0,
    )

    # Parse response
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        return GroundingResult(
            claim=claim,
            supported=result.get("supported", False),
            evidence=evidence_text[:500],
            source_document=source,
            severity=result.get("severity", "critical"),
            reason=result.get("reason", ""),
        )
    except json.JSONDecodeError:
        return GroundingResult(
            claim=claim,
            supported=False,
            severity="major",
            reason="Failed to parse grounding check response",
        )


BATCH_GROUNDING_PROMPT = """You are a strict fact-checker evaluating educational lesson claims against knowledge base evidence.

EVIDENCE FROM KNOWLEDGE BASE:
{evidence}

CLAIMS TO EVALUATE:
{claims_list}

For each claim:
1. Determine if it is fully supported by the evidence (supported: true), or if it is false, unsupported, or contradicts the evidence (supported: false).
2. For unsupported or false claims, specify severity: "critical" (direct contradiction, major hallucination, or false claim) or "major" (unverified assertion), and provide a concise reason explaining the error or contradiction.
3. For supported claims, set severity: "minor" and reason: "Supported by knowledge base evidence".

Return a valid JSON array of objects matching this exact schema:
[
  {{"claim": "exact claim text", "supported": true, "severity": "minor", "reason": "Supported by knowledge base evidence"}},
  {{"claim": "exact claim text", "supported": false, "severity": "critical", "reason": "Contradicts evidence: ..."}}
]
Respond ONLY with the JSON array, no extra markdown or text."""


async def run_grounding_evaluation(
    lesson_data: dict[str, Any],
) -> list[GroundingResult]:
    """Run the complete grounding evaluation pipeline.

    1. Extract claims from the lesson (take top 5 key claims)
    2. Search the knowledge base for relevant evidence
    3. Batch verify claims against evidence in 1 single LLM call
    """
    lesson = GeneratedLesson(**lesson_data)

    # Build full lesson text
    parts = [lesson.title]
    for section in lesson.sections:
        parts.append(f"## {section.heading}\n{section.content}")
    lesson_text = "\n\n".join(parts)

    llm = LLMProvider()
    metrics = MetricsCollector()
    embedding_provider = EmbeddingProvider(metrics=metrics)
    vector_manager = PgVectorManager()
    retrieval = RetrievalPipeline(embedding_provider, vector_manager, metrics)

    try:
        # Step 1: Extract claims
        all_claims = await extract_claims(lesson_text, llm)
        # Cap to top 5 key claims to avoid rate limiting and excessive token usage
        claims = all_claims[:5] if len(all_claims) > 5 else all_claims
        logger.info("claims_extracted", count=len(claims), total_extracted=len(all_claims))

        if not claims:
            return []

        # Step 2: Retrieve relevant evidence for claims from knowledge base
        all_evidence_texts: list[str] = []
        sources: list[str] = []
        for claim in claims:
            evidence_results = await retrieval.retrieve(
                query=claim,
                top_k=2,
                rerank=True,
            )
            for r in evidence_results:
                txt = r.get("text", "")
                if txt and txt not in all_evidence_texts:
                    all_evidence_texts.append(txt)
                src = r.get("source", "")
                if src and src not in sources:
                    sources.append(src)

        combined_evidence = (
            "\n\n---\n\n".join(all_evidence_texts)
            if all_evidence_texts
            else "No relevant evidence found in the knowledge base."
        )
        primary_source = ", ".join(sources) if sources else "knowledge_base"

        # Step 3: Batch check grounding in 1 single LLM call
        claims_formatted = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
        prompt = BATCH_GROUNDING_PROMPT.format(
            evidence=combined_evidence[:4000],
            claims_list=claims_formatted,
        )

        response = await llm.generate(
            system_prompt="You are a strict educational fact-checker. Return JSON array only.",
            user_prompt=prompt,
            node_name="grounding_batch_check",
            temperature=0.0,
        )

        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        grounding_results: list[GroundingResult] = []
        try:
            parsed = json.loads(cleaned, strict=False)
            if isinstance(parsed, list):
                for item in parsed:
                    grounding_results.append(GroundingResult(
                        claim=item.get("claim", ""),
                        supported=item.get("supported", False),
                        evidence=combined_evidence[:500],
                        source_document=primary_source,
                        severity=item.get("severity", "critical"),
                        reason=item.get("reason", ""),
                    ))
        except json.JSONDecodeError:
            logger.warning("batch_grounding_parse_failed_falling_back_to_individual")
            for claim in claims[:3]:
                res = await check_claim_grounding(claim, combined_evidence, primary_source, llm)
                grounding_results.append(res)

        unsupported = sum(1 for r in grounding_results if not r.supported)
        logger.info(
            "grounding_evaluation_completed",
            total_claims=len(grounding_results),
            supported=len(grounding_results) - unsupported,
            unsupported=unsupported,
        )

        return grounding_results

    finally:
        await vector_manager.close()
