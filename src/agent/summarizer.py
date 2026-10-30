"""
Final Result Synthesizer and Summarizer Node.

Aggregates step results into a coherent final response, updates
the run record in the database, and marks completion.
"""

from __future__ import annotations

from typing import Any, Optional

from src.agent.state import AgentState
from src.config.settings import get_settings
from src.db.repository import ExecutionRepository


def summarize_node(state: AgentState, repo: Optional[ExecutionRepository] = None) -> dict[str, Any]:
    """
    LangGraph node: produces the final result summary from execution steps.
    """
    user_goal = state.get("user_goal", "")
    run_id = state.get("run_id", "default_run")
    step_results = state.get("step_results", [])
    total_tokens = state.get("total_tokens", 0)
    total_duration = round(state.get("total_duration", 0.0), 2)
    current_status = state.get("status", "completed")

    successes = sum(1 for s in step_results if s.get("tool_success") == 1)
    failures = sum(1 for s in step_results if s.get("tool_success") == 0)

    # Format synthesized response
    lines = [
        f"### Task Execution Summary: {user_goal}\n",
        f"- **Status:** `{current_status.upper()}`",
        f"- **Steps Executed:** {len(step_results)} (Successes: {successes}, Failures: {failures})",
        f"- **Total Duration:** {total_duration}s",
        f"- **Estimated Tokens:** {total_tokens}\n",
        "#### Step Outcomes:",
    ]

    for s in step_results:
        flag = "✅" if s.get("tool_success") == 1 else "❌"
        tool = s.get("tool_called")
        order = s.get("step_order")
        out_preview = (s.get("tool_output") or s.get("error_message") or "").strip()
        if len(out_preview) > 300:
            out_preview = out_preview[:300] + "... [truncated]"
        lines.append(f"{flag} **Step {order} (`{tool}`):**")
        if out_preview:
            lines.append(f"```\n{out_preview}\n```")

    final_result_text = "\n".join(lines)

    # Update database if repo provided
    if repo is not None:
        try:
            repo.update_run_status(
                run_id=run_id,
                status=current_status,
                final_result=final_result_text,
                error_message=state.get("error_message"),
            )
            repo.update_run_totals(run_id)
        except Exception:
            pass

    return {
        "final_result": final_result_text,
        "status": current_status,
    }
