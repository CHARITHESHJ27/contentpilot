"""Integration tests for the LangGraph workflow."""

import pytest
from src.graph.workflow import compile_workflow

@pytest.mark.asyncio
async def test_workflow_compilation():
    """Test that the workflow compiles correctly."""
    workflow = compile_workflow()
    assert workflow is not None

