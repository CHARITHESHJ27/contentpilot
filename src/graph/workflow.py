"""LangGraph workflow definition.

Constructs the complete state machine with conditional edges
for retry control. The retry limit is enforced by APPLICATION CODE,
not by the LLM.
"""

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from src.graph.nodes.aggregate_evaluation import aggregate_evaluation
from src.graph.nodes.deterministic_checks import deterministic_quality_check
from src.graph.nodes.failure_analysis import failure_analysis
from src.graph.nodes.finalize import finalize
from src.graph.nodes.generate_lesson import generate_lesson
from src.graph.nodes.grounding_evaluation import grounding_evaluation
from src.graph.nodes.load_memory import load_memory
from src.graph.nodes.plan_curriculum import plan_curriculum
from src.graph.nodes.regenerate_lesson import regenerate_lesson
from src.graph.nodes.reject import reject
from src.graph.nodes.retrieve_knowledge import retrieve_knowledge
from src.graph.nodes.semantic_evaluation import semantic_evaluation
from src.graph.nodes.validate_structure import validate_structure
from src.graph.state import ContentPilotStateDict
from src.observability import get_logger

logger = get_logger(__name__)


def _route_after_evaluation(state: dict[str, Any]) -> Literal["finalize", "failure_analysis", "reject"]:
    """Conditional edge after aggregate_evaluation.

    Routing decision is DETERMINISTIC (application code, not LLM):
    - PASS → finalize
    - FAIL + retry_count < max_retries → failure_analysis → regenerate
    - FAIL + retry_count >= max_retries → reject
    """
    eval_result = state.get("evaluation_result", {})
    if isinstance(eval_result, dict):
        overall_passed = eval_result.get("overall_passed", False)
    else:
        overall_passed = eval_result.overall_passed

    if overall_passed:
        logger.info("routing_to_finalize", run_id=state.get("run_id"))
        return "finalize"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count < max_retries:
        logger.info(
            "routing_to_failure_analysis",
            run_id=state.get("run_id"),
            retry_count=retry_count,
            max_retries=max_retries,
        )
        return "failure_analysis"
    else:
        logger.warning(
            "routing_to_reject",
            run_id=state.get("run_id"),
            retry_count=retry_count,
            max_retries=max_retries,
        )
        return "reject"


def build_workflow() -> StateGraph:
    """Construct the ContentPilot LangGraph workflow.

    Returns a compiled StateGraph ready for execution.
    """
    workflow = StateGraph(ContentPilotStateDict)

    # --- Add all 13 nodes ---
    workflow.add_node("load_memory", load_memory)
    workflow.add_node("plan_curriculum", plan_curriculum)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("generate_lesson", generate_lesson)
    workflow.add_node("validate_structure", validate_structure)
    workflow.add_node("deterministic_quality_check", deterministic_quality_check)
    workflow.add_node("grounding_evaluation", grounding_evaluation)
    workflow.add_node("semantic_evaluation", semantic_evaluation)
    workflow.add_node("aggregate_evaluation", aggregate_evaluation)
    workflow.add_node("failure_analysis", failure_analysis)
    workflow.add_node("regenerate_lesson", regenerate_lesson)
    workflow.add_node("finalize", finalize)
    workflow.add_node("reject", reject)

    # --- Set entry point ---
    workflow.set_entry_point("load_memory")

    # --- Linear edges (happy path) ---
    workflow.add_edge("load_memory", "plan_curriculum")
    workflow.add_edge("plan_curriculum", "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge", "generate_lesson")
    workflow.add_edge("generate_lesson", "validate_structure")
    workflow.add_edge("validate_structure", "deterministic_quality_check")
    workflow.add_edge("deterministic_quality_check", "grounding_evaluation")
    workflow.add_edge("grounding_evaluation", "semantic_evaluation")
    workflow.add_edge("semantic_evaluation", "aggregate_evaluation")

    # --- Conditional edge after evaluation (PASS/FAIL gate) ---
    workflow.add_conditional_edges(
        "aggregate_evaluation",
        _route_after_evaluation,
        {
            "finalize": "finalize",
            "failure_analysis": "failure_analysis",
            "reject": "reject",
        },
    )

    # --- Retry loop ---
    workflow.add_edge("failure_analysis", "regenerate_lesson")
    # After regeneration, go back to validation (re-evaluate)
    workflow.add_edge("regenerate_lesson", "validate_structure")

    # --- Terminal nodes ---
    workflow.add_edge("finalize", END)
    workflow.add_edge("reject", END)

    return workflow


def compile_workflow():
    """Build and compile the workflow for execution."""
    workflow = build_workflow()
    return workflow.compile()
