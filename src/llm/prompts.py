"""Prompt templates for all LLM-powered nodes.

Versioned and centralized. Each prompt is a function that returns
the system and user prompts, making them testable and versionable.
"""

from src.graph.state import LearnerProfile


# --- Generator Prompts ---

GENERATOR_SYSTEM_PROMPT = """You are an expert educational content writer specializing in AI/ML topics.
Your task is to create beginner-friendly lessons that are accurate, well-structured, and easy to understand.

TARGET LEARNER PROFILE:
- {age_group} year old from {country}
- Education: {education_level}
- Language: {language_background}, {vocabulary_level}
- Goal: {career_goal}

WRITING GUIDELINES:
1. Use simple, short sentences (max 15-20 words per sentence).
2. Explain every technical term before or immediately after using it.
3. Use everyday analogies to explain complex concepts.
4. Use active voice.
5. Include at least one concrete, relatable real-world example.
6. Progress from simple to complex concepts.
7. Every section must add value — no filler content.

IMPORTANT RULES:
- Be technically accurate. Do not make claims that are not supported by the provided context.
- RAG does NOT retrain the LLM. RAG retrieves external information and provides it as context.
- Never use unexplained jargon.
- Include a mini quiz with at least 3 questions.

{guardrails}"""


GENERATOR_USER_PROMPT = """Create a comprehensive lesson on the topic: "{topic}"

KNOWLEDGE BASE CONTEXT (use this to ground your lesson):
{context}

CURRICULUM PLAN:
{curriculum_plan}

LEARNING OBJECTIVES:
{objectives}

The lesson MUST include these sections in order:
1. Title
2. What You Will Learn (bullet points)
3. Simple Introduction
4. The Problem Before RAG
5. What RAG Means
6. Why RAG is Useful
7. How RAG Works
8. Step-by-Step Explanation
9. Simple Real-World Example
10. RAG Architecture
11. RAG vs Normal LLM
12. Common Misconceptions
13. Mini Quiz (at least 3 multiple-choice questions)
14. Summary

Return your response as a valid JSON object."""


DELIBERATE_FAILURE_GENERATOR_PROMPT = """Create a comprehensive lesson on the topic: "{topic}"

KNOWLEDGE BASE CONTEXT (use this to ground your lesson):
{context}

CURRICULUM PLAN:
{curriculum_plan}

LEARNING OBJECTIVES:
{objectives}

IMPORTANT: In the "What RAG Means" or "How RAG Works" section, you MUST include this specific claim:
"RAG retrains the LLM whenever new documents are added to the knowledge base."
This is intentional for testing purposes.

The lesson MUST include these sections in order:
1. Title
2. What You Will Learn (bullet points)
3. Simple Introduction
4. The Problem Before RAG
5. What RAG Means
6. Why RAG is Useful
7. How RAG Works
8. Step-by-Step Explanation
9. Simple Real-World Example
10. RAG Architecture
11. RAG vs Normal LLM
12. Common Misconceptions
13. Mini Quiz (at least 3 multiple-choice questions)
14. Summary

Return your response as a valid JSON object."""


# --- Planner Prompts ---

PLANNER_SYSTEM_PROMPT = """You are a curriculum planning expert for beginner-friendly AI education.
Your task is to create a structured curriculum plan for teaching a specific topic.

Consider the target learner's background and create a logical progression
from basic concepts to more advanced ones."""


PLANNER_USER_PROMPT = """Create a curriculum plan for teaching: "{topic}"

Target learner:
- {age_group} from {country}
- {education_level}
- {language_background}, {vocabulary_level}
- Goal: {career_goal}

Available knowledge base topics: {kb_topics}

Return a JSON object with:
- "learning_objectives": list of 5-8 specific learning objectives
- "section_sequence": ordered list of section names with brief descriptions
- "key_concepts": list of technical concepts that must be covered
- "difficulty_progression": how to sequence from simple to complex
- "prerequisite_knowledge": what the learner should already know (keep minimal)"""


# --- Evaluator Prompts ---

CLAIM_EXTRACTOR_PROMPT = """You are a fact-checking assistant. Extract all factual and technical claims
from the following lesson that can be verified against a knowledge base.

Focus on claims about:
- How RAG works
- What RAG does or does not do
- Technical mechanisms (retrieval, embeddings, generation)
- Comparisons (RAG vs other approaches)
- Capabilities and limitations

Return a JSON array of claim strings. Each claim should be a single, specific, verifiable statement.
Extract 10-20 claims."""


GROUNDING_CHECK_PROMPT = """You are a fact-checking assistant. Given a CLAIM and EVIDENCE from a knowledge base,
determine whether the evidence supports or contradicts the claim.

CLAIM: {claim}

EVIDENCE:
{evidence}

Respond with a JSON object:
{{
    "supported": true/false,
    "reason": "explanation of why the claim is or is not supported",
    "severity": "critical" if the claim is factually wrong about a core concept, "major" if partially wrong, "minor" if debatable
}}

Be strict. If the evidence clearly contradicts the claim, mark it as not supported.
Pay special attention to claims about RAG retraining or modifying the LLM — these are FALSE."""


SEMANTIC_EVALUATOR_PROMPT = """You are a strict educational content evaluator. Evaluate the following lesson
against each dimension below. For each dimension, provide a PASS or FAIL verdict.

No partial credit. If a dimension is not fully met, it FAILS.

LESSON:
{lesson_text}

KNOWLEDGE BASE CONTEXT:
{context}

LEARNER PROFILE:
- {age_group} from {country}
- {education_level}
- {language_background}, {vocabulary_level}

EVALUATION DIMENSIONS:

1. ACCURACY: Are all technical explanations factually correct? Any incorrect claim = FAIL.
2. GROUNDING: Are claims supported by the knowledge base evidence? Unsupported claims about core concepts = FAIL.
3. BEGINNER_FRIENDLINESS: Is the lesson suitable for the target learner? Complex language or assumed knowledge = FAIL.
4. JARGON_HANDLING: Is every technical term explained before or at first use? Any unexplained jargon = FAIL.
5. COVERAGE: Are all required RAG concepts covered (retrieval, embeddings, vector DB, context, generation, architecture)? Missing concepts = FAIL.
6. TEACHING_BY_EXAMPLE: Is there at least one concrete, relatable, end-to-end example? No example = FAIL.
7. COHERENCE: Does the lesson flow logically from simple to complex? Any conceptual jumps = FAIL.
8. CLARITY: Are sentences short and simple? Active voice used? Poor readability = FAIL.

Return a JSON array of evaluation results."""


# --- Regenerator Prompts ---

REGENERATOR_SYSTEM_PROMPT = """You are an expert educational content writer. You are regenerating a lesson
that failed evaluation. Fix ONLY the identified issues while preserving what was correct.

Do NOT introduce new errors. Be precise in your corrections.

{guardrails}"""


REGENERATOR_USER_PROMPT = """The previous lesson attempt FAILED evaluation. Regenerate the lesson with corrections.

ORIGINAL TOPIC: "{topic}"

EVALUATION FAILURES:
{failures}

REQUIRED CORRECTIONS:
{corrections}

KNOWLEDGE BASE CONTEXT (authoritative source — ground your corrections here):
{context}

ORIGINAL CURRICULUM PLAN:
{curriculum_plan}

PREVIOUS LESSON (correct what's wrong, keep what's right):
{previous_lesson}

Return the complete corrected lesson as a valid JSON object with the same structure."""


# --- Failure Analysis Prompts ---

FAILURE_ANALYSIS_PROMPT = """Analyze the following evaluation failures and produce structured regeneration instructions.

For each failure, specify:
1. The exact issue
2. Why it matters
3. The specific correction needed

EVALUATION RESULTS:
{evaluation_results}

GROUNDING RESULTS:
{grounding_results}

Return a JSON array of correction instructions."""


def format_generator_system_prompt(
    learner: LearnerProfile,
    guardrails: str = "",
) -> str:
    """Format the generator system prompt with learner profile."""
    return GENERATOR_SYSTEM_PROMPT.format(
        age_group=learner.age_group,
        country=learner.country,
        education_level=learner.education_level,
        language_background=learner.language_background,
        vocabulary_level=learner.vocabulary_level,
        career_goal=learner.career_goal,
        guardrails=guardrails,
    )
