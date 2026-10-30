"""
Execution Engine Node for the Agentic AI Task Planner.

Executes the current step of the plan using the tool registry, logs
results to the SQLite repository, and manages state transitions.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from src.agent.state import AgentState, StepResult
from src.agent.tools.base import ToolResult
from src.agent.tools.registry import execute_tool, is_sensitive_tool
from src.db.repository import ExecutionRepository


def execute_step_node(state: AgentState, repo: Optional[ExecutionRepository] = None) -> dict[str, Any]:
    """
    LangGraph node: executes the step at state['current_step_index'].

    Parameters
    ----------
    state : AgentState
        Current workflow state.
    repo : ExecutionRepository, optional
        Repository for persisting traces. Created if None.

    Returns
    -------
    dict[str, Any]
        State updates for LangGraph.
    """
    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)
    run_id = state.get("run_id", "default_run")
    step_results = list(state.get("step_results", []))
    total_tokens = state.get("total_tokens", 0)
    total_duration = state.get("total_duration", 0.0)
    retry_count = state.get("retry_count", 0)

    if idx >= len(plan):
        # All steps completed
        return {"status": "completed"}

    current_step = plan[idx]
    tool_called = current_step["tool_called"]
    tool_input = current_step.get("tool_input", {})
    requires_approval = current_step.get("requires_approval", False) or is_sensitive_tool(tool_called)

    # Human-In-The-Loop gate check
    is_auto = state.get("auto_approve", False)
    human_approved = state.get("human_approved")
    is_authorized = is_auto or (human_approved is True)

    if requires_approval and not is_authorized:
        # Halt execution until approved by human
        return {
            "status": "awaiting_approval",
        }

    # Execute the tool
    tool_res: ToolResult = execute_tool(tool_called, **tool_input)

    # Build StepResult
    step_result: StepResult = {
        "step_order": current_step["step_order"],
        "tool_called": tool_called,
        "tool_input": tool_input,
        "tool_output": tool_res.output,
        "tool_success": 1 if tool_res.success else 0,
        "tokens_used": tool_res.tokens_used,
        "duration_s": tool_res.duration_s,
        "retry_count": retry_count,
        "error_message": tool_res.error,
        "requires_approval": requires_approval,
        "approved": human_approved if requires_approval else None,
    }

    # Persist to SQLite if repo is available
    if repo is not None:
        try:
            repo.add_step(
                run_id=run_id,
                step_order=current_step["step_order"],
                tool_called=tool_called,
                tool_success=1 if tool_res.success else 0,
                tool_input=json.dumps(tool_input),
                tool_output=tool_res.output,
                planned_action=current_step.get("description"),
                tokens_used=tool_res.tokens_used,
                duration_s=tool_res.duration_s,
                retry_count=retry_count,
                error_message=tool_res.error,
                requires_approval=requires_approval,
                approved=human_approved if requires_approval else None,
            )
            repo.update_run_totals(run_id)
        except Exception:
            pass

    step_results.append(step_result)
    updated_tokens = total_tokens + tool_res.tokens_used
    updated_duration = total_duration + tool_res.duration_s

    if tool_res.success:
        # Step succeeded: advance index, reset retries
        next_idx = idx + 1
        is_done = next_idx >= len(plan)
        return {
            "current_step_index": next_idx,
            "step_results": step_results,
            "total_tokens": updated_tokens,
            "total_duration": updated_duration,
            "retry_count": 0,
            "human_approved": None,
            "status": "completed" if is_done else "running",
        }
    else:
        # Step failed: preserve index for error_handler retry
        return {
            "step_results": step_results,
            "total_tokens": updated_tokens,
            "total_duration": updated_duration,
            "status": "running",
            "error_message": tool_res.error,
        }
