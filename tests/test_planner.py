"""
Unit tests for the Planner module (src.agent.planner).
"""

from __future__ import annotations

import pytest

from src.agent.planner import _heuristic_planner, create_plan, plan_node
from src.agent.state import AgentState


class TestPlanner:
    """Test task decomposition and plan creation."""

    def test_plan_math_goal(self):
        plan = create_plan("Calculate sqrt(144) + 25")
        assert len(plan) >= 1
        tools = [s["tool_called"] for s in plan]
        assert "calc" in tools

    def test_plan_data_analysis_goal(self):
        plan = create_plan("Analyze the dataset.csv file and provide a statistical summary")
        assert len(plan) >= 2
        tools = [s["tool_called"] for s in plan]
        assert "file_read" in tools or "data_analysis" in tools

    def test_plan_web_search_goal(self):
        plan = create_plan("Research LangGraph architecture patterns")
        assert len(plan) >= 1
        tools = [s["tool_called"] for s in plan]
        assert "web_search" in tools

    def test_plan_sensitive_tools_flagged(self):
        """Code execution and email drafting must be marked as requiring approval."""
        plan = create_plan("Draft an email to the client summarizing our progress")
        email_step = next((s for s in plan if s["tool_called"] == "email_draft"), None)
        assert email_step is not None
        assert email_step["requires_approval"] is True

        code_plan = create_plan("Run a python script to process data")
        code_step = next((s for s in code_plan if s["tool_called"] == "code_exec"), None)
        assert code_step is not None
        assert code_step["requires_approval"] is True

    def test_plan_node_langgraph_integration(self):
        state: AgentState = {
            "run_id": "test_run",
            "user_goal": "Calculate 50 * 20",
            "plan": [],
            "current_step_index": 0,
            "step_results": [],
            "retry_count": 0,
            "max_retries": 2,
            "status": "planning",
            "final_result": None,
            "error_message": None,
            "total_tokens": 0,
            "total_duration": 0.0,
            "human_approved": None,
        }
        res = plan_node(state)
        assert res["status"] == "running"
        assert len(res["plan"]) >= 1
        assert res["current_step_index"] == 0
