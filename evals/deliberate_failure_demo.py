"""Deliberate failure demo script.

This script demonstrates the self-evaluating pipeline by:
1. Generating a lesson with an intentional error (RAG retrains the LLM)
2. The evaluator catches it
3. The system regenerates with corrections
4. The corrected lesson passes evaluation

Usage:
    python -m evals.deliberate_failure_demo

Or via API:
    POST /api/runs {"topic": "...", "demo_mode": "deliberate_failure"}
"""

import asyncio
import json
import sys

from src.graph.workflow import compile_workflow
from src.observability import setup_logging


async def run_demo():
    """Execute the deliberate failure demonstration."""
    setup_logging("INFO")

    print("\n" + "=" * 60)
    print("  ContentPilot — Deliberate Failure Demo")
    print("=" * 60)

    initial_state = {
        "run_id": "demo-001",
        "topic": "Introduction to RAG (Retrieval-Augmented Generation)",
        "learner_profile": {
            "age_group": "17-18",
            "education_level": "12th grade graduate",
            "language_background": "non-English-medium",
            "vocabulary_level": "limited English",
            "career_goal": "start an AI career",
            "country": "India",
        },
        "demo_mode": "deliberate_failure",
        "max_retries": 2,
        "prompt_version": "1.0.0",
        "rubric_version": "1.0.0",
        "knowledge_base_version": "1.0.0",
        "model_version": "gemini-3.5-flash",
        "embedding_version": "gemini-embedding-001",
    }

    print("\n📝 Starting generation with DELIBERATE ERROR injection...")
    print(f"   Topic: {initial_state['topic']}")
    print(f"   Demo mode: {initial_state['demo_mode']}")
    print(f"   Max retries: {initial_state['max_retries']}")
    print()

    workflow = compile_workflow()
    final_state = await workflow.ainvoke(initial_state)

    # Report results
    print("\n" + "=" * 60)
    print("  DEMO RESULTS")
    print("=" * 60)

    status = final_state.get("final_status", "unknown")
    retries = final_state.get("retry_count", 0)
    versions = len(final_state.get("lesson_versions", []))

    print(f"\n  Final Status: {status.upper()}")
    print(f"  Lesson Versions: {versions}")
    print(f"  Retries Used: {retries}")

    # Show evaluation result
    eval_result = final_state.get("evaluation_result", {})
    if eval_result:
        passed = eval_result.get("overall_passed", False)
        failures = eval_result.get("critical_failures", [])
        print(f"\n  Evaluation Passed: {'✓ YES' if passed else '✗ NO'}")
        if failures:
            print(f"  Critical Failures ({len(failures)}):")
            for f in failures:
                print(f"    ✗ {f}")

    # Show lesson versions progression
    print("\n  Lesson Version History:")
    for lv in final_state.get("lesson_versions", []):
        regen = " (regenerated)" if lv.get("regenerated") else ""
        print(f"    v{lv.get('version')}{regen} — {lv.get('created_at', 'N/A')}")

    print("\n" + "=" * 60)

    if status == "shipped":
        print("  ✓ SUCCESS: Error was caught, lesson was regenerated and shipped!")
    elif status == "rejected":
        print("  ✗ REJECTED: Error was caught but could not be fixed within retry limit.")
    else:
        print(f"  ⚠ UNEXPECTED STATUS: {status}")

    print("=" * 60 + "\n")

    return final_state


if __name__ == "__main__":
    result = asyncio.run(run_demo())
    sys.exit(0 if result.get("final_status") == "shipped" else 1)
