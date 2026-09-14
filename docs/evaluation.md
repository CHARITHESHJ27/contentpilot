# Evaluation Strategy

ContentPilot uses a **4-layer evaluation stack** to ensure that all generated content meets strict quality, safety, and factual correctness standards.

## Layer 1: Structural Validation (Pydantic)
Enforces the base shape of the data. The LLM must output valid JSON matching the Pydantic schema. Checks include:
- All required fields are present (title, sections, summary, quiz).
- The quiz contains at least 3 questions with 4 options each.
- `correct_option_index` is valid.

## Layer 2: Deterministic Quality Checks
Fast, cheap rule-based checks that catch obvious failures without invoking an LLM. Checks include:
- **Length**: Word count must be between 1500 and 8000.
- **Jargon Density**: Ratio of complex words to total words must be ≤ 15%.
- **Prohibited Claims**: Regex search for forbidden phrases (e.g., "RAG retrains the LLM").
- **Required Concepts**: Ensures critical RAG concepts are mentioned in the text.

## Layer 3: Grounding Evaluation
Fact-checking against the canonical knowledge base.
1. An LLM extracts factual claims from the generated lesson.
2. The claims are searched against the pgvector knowledge chunks.
3. An LLM evaluator determines if the retrieved evidence supports, contradicts, or is silent on the claim.

## Layer 4: Semantic Evaluation (LLM Judge)
A comprehensive LLM evaluation against a pedagogical rubric. Dimensions checked:
- Accuracy
- Beginner Friendliness
- Jargon Handling
- Coverage
- Teaching by Example
- Coherence
- Clarity

## The Final Gate
The system uses a strict **hard pass/fail** logic. There is no "average score". If any check across the 4 layers raises a **critical** failure, the lesson is rejected and sent back for regeneration (if retries remain).
