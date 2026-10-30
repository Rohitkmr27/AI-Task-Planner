"""
Integration tests for the LangGraph state machine (src.agent.graph).
"""

from __future__ import annotations

import pytest

from src.agent.graph import build_agent_graph, run_agent
from src.db.repository import ExecutionRepository


@pytest.fixture
def repo() -> ExecutionRepository:
    return ExecutionRepository(db_path=":memory:")


class TestAgentGraph:
    """End-to-end integration tests for LangGraph state machine."""

    def test_run_agent_math_task(self, repo: ExecutionRepository):
        final_state = run_agent("Calculate sqrt(256) * 4", repo=repo, auto_approve=True)
        assert final_state["status"] == "completed"
        assert len(final_state["step_results"]) >= 1
        assert final_state["final_result"] is not None
        assert "64.0" in final_state["final_result"]

        # Verify recorded in DB
        runs = repo.list_runs()
        assert len(runs) == 1
        assert runs[0].status == "completed"
        assert runs[0].successful_steps >= 1

    def test_run_agent_data_analysis_task(self, repo: ExecutionRepository):
        final_state = run_agent(
            "Inspect dataset.csv and provide a summary of columns",
            repo=repo,
            auto_approve=True,
        )
        assert final_state["status"] == "completed"
        assert len(final_state["step_results"]) >= 1
        assert final_state["final_result"] is not None
        assert "task_id" in final_state["final_result"] or "dataset.csv" in final_state["final_result"]

    def test_run_agent_pauses_for_sensitive_email_task_without_auto_approve(self, repo: ExecutionRepository):
        final_state = run_agent(
            "Draft an email to supervisor@test.com with status update",
            repo=repo,
            auto_approve=False,  # Should pause
        )
        assert final_state["status"] == "awaiting_approval"
        # The step should not have executed yet
        assert len(final_state["step_results"]) == 0

    def test_run_agent_executes_sensitive_email_task_with_auto_approve(self, repo: ExecutionRepository):
        final_state = run_agent(
            "Draft an email to supervisor@test.com with status update",
            repo=repo,
            auto_approve=True,
        )
        assert final_state["status"] == "completed"
        assert len(final_state["step_results"]) >= 1
        # Check watermark
        email_result = next(
            (s for s in final_state["step_results"] if s["tool_called"] == "email_draft"),
            None,
        )
        assert email_result is not None
        assert "DRAFT" in email_result["tool_output"]

    def test_error_recovery_and_step_failure(self, repo: ExecutionRepository):
        # We can verify error recovery with a task containing an invalid calc expression
        final_state = run_agent(
            "Calculate 10 / 0",
            repo=repo,
            auto_approve=True,
            max_retries=1,
        )
        # Should attempt retries and reach terminal state without uncaught crash
        assert final_state["status"] in ("completed", "failed")
        assert len(final_state["step_results"]) >= 1
        assert final_state["final_result"] is not None
