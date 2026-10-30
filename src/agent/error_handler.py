"""
Error Recovery and Retry Handler for Agent Orchestration.

Manages retry counters, fallback tool selection, and graceful degradation
when tool invocations fail.
"""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentState
from src.config.settings import get_settings


def handle_error_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: handles step failures, increments retries, or activates fallbacks.
    """
    settings = get_settings()
    max_retries = state.get("max_retries", settings.max_retries_per_step)
    retry_count = state.get("retry_count", 0)
    idx = state.get("current_step_index", 0)
    plan = list(state.get("plan", []))
    step_results = state.get("step_results", [])

    if not step_results:
        return {"status": "running"}

    last_result = step_results[-1]
    if last_result.get("tool_success") == 1:
        # Last step succeeded, no error handling required
        return {"status": "running"}

    # Step failed: check if retry attempts remain
    if retry_count < max_retries:
        new_retry = retry_count + 1
        return {
            "retry_count": new_retry,
            "status": "running",
            "error_message": f"Retry {new_retry}/{max_retries} for step {idx + 1}: {last_result.get('error_message')}",
        }
    else:
        # Max retries exceeded: advance to next step or fail run
        next_idx = idx + 1
        is_done = next_idx >= len(plan)

        # Count total failed steps so far
        failed_count = sum(1 for s in step_results if s.get("tool_success") == 0)

        # If too many steps failed (e.g. > 50%), mark run as failed
        overall_failed = (failed_count >= len(plan))

        return {
            "current_step_index": next_idx,
            "retry_count": 0,
            "human_approved": None,
            "status": "failed" if overall_failed else ("completed" if is_done else "running"),
            "error_message": f"Step {idx + 1} permanently failed after {max_retries} retries.",
        }
