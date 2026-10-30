"""
Unit tests for the runtime database layer (src.db.models and src.db.repository).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.db.models import init_database, reset_database
from src.db.repository import ExecutionRepository


@pytest.fixture
def repo() -> ExecutionRepository:
    """Fixture providing an in-memory ExecutionRepository for each test."""
    return ExecutionRepository(db_path=":memory:")


class TestDatabaseModels:
    """Test table creation and database connection configuration."""

    def test_init_database_in_memory(self):
        """Database should initialise with WAL, foreign keys, and tables created."""
        conn = init_database(":memory:")
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        assert "execution_runs" in tables
        assert "execution_steps" in tables

        # Foreign keys should be enabled
        cursor.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_reset_database(self):
        """reset_database should drop and recreate tables."""
        conn = init_database(":memory:")
        # Insert a run
        conn.execute(
            "INSERT INTO execution_runs (run_id, user_goal, created_at) VALUES ('R1', 'Goal', '2026-01-01')"
        )
        conn.commit()

        # Reset
        conn = reset_database(":memory:")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM execution_runs;")
        assert cursor.fetchone()[0] == 0
        conn.close()


class TestExecutionRepository:
    """Test CRUD operations and analytics in ExecutionRepository."""

    def test_create_and_get_run(self, repo: ExecutionRepository):
        """Should create a run and retrieve it as a RunRecord."""
        plan = [{"step": 1, "tool": "web_search", "action": "Search"}]
        run_id = repo.create_run(user_goal="Research AI agents", plan=plan)

        assert run_id is not None
        run = repo.get_run(run_id)
        assert run is not None
        assert run.run_id == run_id
        assert run.user_goal == "Research AI agents"
        assert run.status == "pending"
        assert "web_search" in (run.plan_json or "")
        assert run.created_at is not None
        assert run.completed_at is None

    def test_update_run_status(self, repo: ExecutionRepository):
        """Status updates should set completed_at on terminal states."""
        run_id = repo.create_run(user_goal="Test run")

        repo.update_run_status(run_id, "running")
        run = repo.get_run(run_id)
        assert run.status == "running"
        assert run.completed_at is None

        repo.update_run_status(run_id, "completed", final_result="All tasks done.")
        run = repo.get_run(run_id)
        assert run.status == "completed"
        assert run.completed_at is not None
        assert run.final_result == "All tasks done."

    def test_list_runs_and_count(self, repo: ExecutionRepository):
        """list_runs should return runs ordered by created_at DESC with filtering."""
        repo.create_run(user_goal="Run 1")
        r2 = repo.create_run(user_goal="Run 2")
        repo.update_run_status(r2, "completed")

        all_runs = repo.list_runs()
        assert len(all_runs) == 2
        assert repo.count_runs() == 2

        completed_runs = repo.list_runs(status="completed")
        assert len(completed_runs) == 1
        assert completed_runs[0].run_id == r2
        assert repo.count_runs(status="completed") == 1
        assert repo.count_runs(status="failed") == 0

    def test_add_and_get_steps(self, repo: ExecutionRepository):
        """Should record steps and retrieve them in order."""
        run_id = repo.create_run(user_goal="Data task")

        step1_id = repo.add_step(
            run_id=run_id,
            step_order=1,
            tool_called="file_read",
            tool_success=1,
            tool_input="dataset.csv",
            tool_output="500 rows loaded",
            tokens_used=500,
            duration_s=1.2,
        )

        step2_id = repo.add_step(
            run_id=run_id,
            step_order=2,
            tool_called="calc",
            tool_success=1,
            tool_input="mean(duration)",
            tool_output="7.82",
            tokens_used=120,
            duration_s=0.4,
        )

        steps = repo.get_steps(run_id)
        assert len(steps) == 2
        assert steps[0].step_order == 1
        assert steps[0].tool_called == "file_read"
        assert steps[1].step_order == 2
        assert steps[1].tool_called == "calc"

        single_step = repo.get_step(step1_id)
        assert single_step is not None
        assert single_step.tool_output == "500 rows loaded"

    def test_human_approval_flow(self, repo: ExecutionRepository):
        """Should record sensitive tool approval request and subsequent decision."""
        run_id = repo.create_run(user_goal="Email task")

        step_id = repo.add_step(
            run_id=run_id,
            step_order=1,
            tool_called="email_draft",
            tool_success=0,
            tool_input="subject: Test",
            requires_approval=True,
            approved=None,
        )

        step = repo.get_step(step_id)
        assert step.requires_approval == 1
        assert step.approved is None

        # Human approves
        repo.update_step_approval(step_id, approved=True)
        step = repo.get_step(step_id)
        assert step.approved == 1

    def test_update_run_totals(self, repo: ExecutionRepository):
        """update_run_totals should aggregate step metrics onto the run."""
        run_id = repo.create_run(user_goal="Batch task")

        repo.add_step(
            run_id=run_id, step_order=1, tool_called="calc", tool_success=1,
            tokens_used=1000, duration_s=2.5,
        )
        repo.add_step(
            run_id=run_id, step_order=2, tool_called="web_search", tool_success=0,
            tokens_used=2500, duration_s=5.0,
        )

        repo.update_run_totals(run_id)
        run = repo.get_run(run_id)

        assert run.total_steps == 2
        assert run.successful_steps == 1
        assert run.failed_steps == 1
        assert run.total_tokens == 3500
        assert pytest.approx(run.total_duration, 0.01) == 7.5

    def test_cascade_delete(self, repo: ExecutionRepository):
        """Deleting a run should delete all child steps via foreign key cascade."""
        run_id = repo.create_run(user_goal="To be deleted")
        repo.add_step(run_id=run_id, step_order=1, tool_called="calc", tool_success=1)

        assert len(repo.get_steps(run_id)) == 1

        repo.delete_run(run_id)
        assert repo.get_run(run_id) is None
        assert len(repo.get_steps(run_id)) == 0

    def test_analytics_tool_usage_stats(self, repo: ExecutionRepository):
        """Tool usage stats should compute totals, successes, and averages."""
        r1 = repo.create_run(user_goal="Run 1")
        repo.add_step(run_id=r1, step_order=1, tool_called="calc", tool_success=1, tokens_used=100, duration_s=1.0)
        repo.add_step(run_id=r1, step_order=2, tool_called="calc", tool_success=0, tokens_used=200, duration_s=2.0)
        repo.add_step(run_id=r1, step_order=3, tool_called="web_search", tool_success=1, tokens_used=500, duration_s=3.0)

        stats = repo.get_tool_usage_stats()
        stats_map = {s["tool_called"]: s for s in stats}

        assert "calc" in stats_map
        assert stats_map["calc"]["total_invocations"] == 2
        assert stats_map["calc"]["successes"] == 1
        assert stats_map["calc"]["failures"] == 1
        assert stats_map["calc"]["avg_tokens"] == 150.0
        assert stats_map["calc"]["avg_duration"] == 1.5

        assert "web_search" in stats_map
        assert stats_map["web_search"]["total_invocations"] == 1
        assert stats_map["web_search"]["successes"] == 1

    def test_original_dataset_never_modified_by_db_operations(self, project_root: Path):
        """
        Verify that database operations never modify the original dataset.csv.
        """
        dataset_path = project_root / "dataset.csv"
        mtime_before = dataset_path.stat().st_mtime
        size_before = dataset_path.stat().st_size

        # Perform multiple database operations
        test_db = project_root / "data" / "test_scratch.db"
        repo = ExecutionRepository(db_path=str(test_db))
        run_id = repo.create_run(user_goal="Check dataset isolation")
        repo.add_step(run_id=run_id, step_order=1, tool_called="file_read", tool_success=1)
        repo.update_run_totals(run_id)
        repo.close()

        # Clean up scratch db
        if test_db.exists():
            test_db.unlink()

        # Verify dataset.csv is untouched
        assert dataset_path.stat().st_mtime == mtime_before
        assert dataset_path.stat().st_size == size_before
