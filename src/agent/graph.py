"""
LangGraph StateGraph Orchestration for the Agentic AI Task Planner.

Constructs the cyclical state graph:
START -> planner -> executor <-> error_handler -> summarizer -> END
Supports Human-in-the-Loop interrupts for sensitive tools and checkpointing.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agent.error_handler import handle_error_node
from src.agent.executor import execute_step_node
from src.agent.planner import plan_node
from src.agent.state import AgentState
from src.agent.summarizer import summarize_node
from src.db.repository import ExecutionRepository


def build_agent_graph(repo: Optional[ExecutionRepository] = None, checkpointer: Optional[Any] = None) -> StateGraph:
    """
    Construct the agent execution graph.

    Parameters
    ----------
    repo : ExecutionRepository, optional
        Database repository for persisting execution logs.
    checkpointer : Checkpointer, optional
        LangGraph checkpoint saver for state persistence and HITL resume.

    Returns
    -------
    Compiled StateGraph
    """
    workflow = StateGraph(AgentState)

    # 1. Define nodes
    def _planner(state: AgentState) -> dict[str, Any]:
        result = plan_node(state)
        # Record plan to database
        if repo is not None and result.get("plan"):
            try:
                repo.update_run_plan(state["run_id"], result["plan"])
                repo.update_run_status(state["run_id"], "running")
            except Exception:
                pass
        return result

    def _executor(state: AgentState) -> dict[str, Any]:
        return execute_step_node(state, repo=repo)

    def _error_handler(state: AgentState) -> dict[str, Any]:
        return handle_error_node(state)

    def _summarizer(state: AgentState) -> dict[str, Any]:
        return summarize_node(state, repo=repo)

    workflow.add_node("planner", _planner)
    workflow.add_node("executor", _executor)
    workflow.add_node("error_handler", _error_handler)
    workflow.add_node("summarizer", _summarizer)

    # 2. Add edges and conditional transitions
    workflow.add_edge(START, "planner")

    def route_after_planner(state: AgentState) -> Literal["executor", "summarizer"]:
        if state.get("status") == "running" and state.get("plan"):
            return "executor"
        return "summarizer"

    workflow.add_conditional_edges("planner", route_after_planner)

    def route_after_executor(state: AgentState) -> Literal["executor", "error_handler", "summarizer", "__end__"]:
        status = state.get("status")
        if status == "awaiting_approval":
            # Interrupt: pause and wait for human confirmation
            return END

        if status in ("completed", "failed", "cancelled"):
            return "summarizer"

        step_results = state.get("step_results", [])
        if step_results and step_results[-1].get("tool_success") == 0:
            return "error_handler"

        # Step succeeded and more steps remain
        return "executor"

    workflow.add_conditional_edges("executor", route_after_executor)

    def route_after_error_handler(state: AgentState) -> Literal["executor", "summarizer"]:
        status = state.get("status")
        if status in ("completed", "failed"):
            return "summarizer"
        return "executor"

    workflow.add_conditional_edges("error_handler", route_after_error_handler)

    workflow.add_edge("summarizer", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


def run_agent(
    user_goal: str,
    repo: Optional[ExecutionRepository] = None,
    run_id: Optional[str] = None,
    auto_approve: bool = False,
    max_retries: int = 2,
) -> AgentState:
    """
    Convenience function to run the agent end-to-end on a user goal.

    Parameters
    ----------
    user_goal : str
        The task to execute.
    repo : ExecutionRepository, optional
        Execution database repository.
    run_id : str, optional
        Unique run ID (generated if not provided).
    auto_approve : bool
        If True, automatically approves sensitive actions (for testing/automation).
    max_retries : int
        Maximum retries per failed step.

    Returns
    -------
    AgentState
        Final state after execution.
    """
    if run_id is None:
        run_id = f"run_{uuid.uuid4().hex[:8]}"

    # Record initial run in database
    if repo is not None:
        try:
            repo.create_run(user_goal=user_goal, run_id=run_id)
        except Exception:
            pass

    graph = build_agent_graph(repo=repo)

    initial_state: AgentState = {
        "run_id": run_id,
        "user_goal": user_goal,
        "plan": [],
        "current_step_index": 0,
        "step_results": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "status": "planning",
        "final_result": None,
        "error_message": None,
        "total_tokens": 0,
        "total_duration": 0.0,
        "auto_approve": auto_approve,
        "human_approved": True if auto_approve else None,
    }

    config = {"configurable": {"thread_id": run_id}}
    final_output = graph.invoke(initial_state, config=config)
    return final_output
