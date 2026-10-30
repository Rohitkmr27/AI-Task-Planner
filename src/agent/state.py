"""
Agent state definitions for LangGraph orchestration.

Defines the TypedDict schema tracked across all graph nodes:
planner -> approval_gate -> executor -> error_handler -> summarizer.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict


class PlanStep(TypedDict):
    """A single planned execution step."""
    step_order: int
    tool_called: str
    tool_input: dict[str, Any]
    description: str
    requires_approval: bool


class StepResult(TypedDict):
    """The execution outcome of a single step."""
    step_order: int
    tool_called: str
    tool_input: dict[str, Any]
    tool_output: str
    tool_success: int  # 1 for success, 0 for failure
    tokens_used: int
    duration_s: float
    retry_count: int
    error_message: Optional[str]
    requires_approval: bool
    approved: Optional[bool]


AgentStatus = Literal[
    "pending",
    "planning",
    "running",
    "awaiting_approval",
    "completed",
    "failed",
    "cancelled",
]


class AgentState(TypedDict):
    """
    Complete state passed between LangGraph nodes during task execution.
    """
    run_id: str
    user_goal: str
    plan: list[PlanStep]
    current_step_index: int
    step_results: list[StepResult]
    retry_count: int
    max_retries: int
    status: AgentStatus
    final_result: Optional[str]
    error_message: Optional[str]
    total_tokens: int
    total_duration: float
    auto_approve: bool  # Whether sensitive actions should auto-execute
    human_approved: Optional[bool]  # Set by HITL gate or resume payload
