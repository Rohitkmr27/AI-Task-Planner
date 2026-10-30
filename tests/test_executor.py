"""
Unit tests for the Executor module (src.agent.executor).
"""

from __future__ import annotations

import pytest

from src.agent.executor import execute_step_node
from src.agent.state import AgentState, PlanStep
from src.db.repository import ExecutionRepository


@pytest.fixture
def repo() -> ExecutionRepository:
    return ExecutionRepository(db_path=":memory:")


class TestExecutor:
    """Test step execution, state updates, and SQLite logging."""

    def test_execute_non_sensitive_step_success(self, repo: ExecutionRepository):
        plan: list[PlanStep] = [
            {
                "step_order": 1,
                "tool_called": "calc",
                "tool_input": {"expression": "20 + 22"},
                "description": "Add numbers",
                "requires_approval": False,
            }
        ]
        run_id = repo.create_run(user_goal="Calculate 20+22", plan=plan)

        state: AgentState = {
            "run_id": run_id,
            "user_goal": "Calculate 20+22",
            "plan": plan,
            "current_step_index": 0,
            "step_results": [],
            "retry_count": 0,
            "max_retries": 2,
            "status": "running",
            "final_result": None,
            "error_message": None,
            "total_tokens": 0,
            "total_duration": 0.0,
            "human_approved": None,
        }

        update = execute_step_node(state, repo=repo)
        assert update["status"] == "completed"
        assert update["current_step_index"] == 1
        assert len(update["step_results"]) == 1
        assert update["step_results"][0]["tool_success"] == 1
        assert update["step_results"][0]["tool_output"] == "42"

        # Verify step recorded in SQLite
        db_steps = repo.get_steps(run_id)
        assert len(db_steps) == 1
        assert db_steps[0].tool_called == "calc"
        assert db_steps[0].tool_success == 1

    def test_sensitive_step_pauses_for_approval(self, repo: ExecutionRepository):
        plan: list[PlanStep] = [
            {
                "step_order": 1,
                "tool_called": "email_draft",
                "tool_input": {"to": "boss@co.com", "subject": "Hi", "body": "Hello"},
                "description": "Draft email",
                "requires_approval": True,
            }
        ]
        run_id = repo.create_run(user_goal="Draft email", plan=plan)

        state: AgentState = {
            "run_id": run_id,
            "user_goal": "Draft email",
            "plan": plan,
            "current_step_index": 0,
            "step_results": [],
            "retry_count": 0,
            "max_retries": 2,
            "status": "running",
            "final_result": None,
            "error_message": None,
            "total_tokens": 0,
            "total_duration": 0.0,
            "human_approved": None,  # Not approved yet
        }

        update = execute_step_node(state, repo=repo)
        assert update["status"] == "awaiting_approval"
        assert "step_results" not in update  # Not executed yet

    def test_sensitive_step_executes_when_approved(self, repo: ExecutionRepository):
        plan: list[PlanStep] = [
            {
                "step_order": 1,
                "tool_called": "email_draft",
                "tool_input": {"to": "boss@co.com", "subject": "Hi", "body": "Hello"},
                "description": "Draft email",
                "requires_approval": True,
            }
        ]
        run_id = repo.create_run(user_goal="Draft email", plan=plan)

        state: AgentState = {
            "run_id": run_id,
            "user_goal": "Draft email",
            "plan": plan,
            "current_step_index": 0,
            "step_results": [],
            "retry_count": 0,
            "max_retries": 2,
            "status": "running",
            "final_result": None,
            "error_message": None,
            "total_tokens": 0,
            "total_duration": 0.0,
            "human_approved": True,  # Approved!
        }

        update = execute_step_node(state, repo=repo)
        assert update["status"] == "completed"
        assert len(update["step_results"]) == 1
        assert update["step_results"][0]["tool_success"] == 1
        assert update["step_results"][0]["approved"] is True
