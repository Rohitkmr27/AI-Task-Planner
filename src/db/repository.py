"""
Data access layer for the runtime execution log database.

Provides CRUD operations for execution_runs and execution_steps tables.
All queries use parameterised statements to prevent SQL injection.

Usage:
    from src.db.repository import ExecutionRepository
    repo = ExecutionRepository(db_path=":memory:")
    run_id = repo.create_run(user_goal="Summarise sales data")
    repo.add_step(run_id=run_id, step_order=1, tool_called="file_read", ...)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from src.db.models import get_connection, init_database


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------

class RunRecord:
    """Lightweight wrapper for an execution_runs row."""

    def __init__(self, row: sqlite3.Row):
        self.run_id: str = row["run_id"]
        self.user_goal: str = row["user_goal"]
        self.status: str = row["status"]
        self.plan_json: Optional[str] = row["plan_json"]
        self.created_at: str = row["created_at"]
        self.completed_at: Optional[str] = row["completed_at"]
        self.total_tokens: int = row["total_tokens"]
        self.total_duration: float = row["total_duration"]
        self.total_steps: int = row["total_steps"]
        self.successful_steps: int = row["successful_steps"]
        self.failed_steps: int = row["failed_steps"]
        self.final_result: Optional[str] = row["final_result"]
        self.error_message: Optional[str] = row["error_message"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_goal": self.user_goal,
            "status": self.status,
            "plan_json": self.plan_json,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "total_tokens": self.total_tokens,
            "total_duration": self.total_duration,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "final_result": self.final_result,
            "error_message": self.error_message,
        }


class StepRecord:
    """Lightweight wrapper for an execution_steps row."""

    def __init__(self, row: sqlite3.Row):
        self.id: int = row["id"]
        self.run_id: str = row["run_id"]
        self.step_order: int = row["step_order"]
        self.planned_action: Optional[str] = row["planned_action"]
        self.tool_called: str = row["tool_called"]
        self.tool_input: Optional[str] = row["tool_input"]
        self.tool_output: Optional[str] = row["tool_output"]
        self.tool_success: int = row["tool_success"]
        self.tokens_used: int = row["tokens_used"]
        self.duration_s: float = row["duration_s"]
        self.retry_count: int = row["retry_count"]
        self.error_message: Optional[str] = row["error_message"]
        self.requires_approval: int = row["requires_approval"]
        self.approved: Optional[int] = row["approved"]
        self.created_at: str = row["created_at"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "step_order": self.step_order,
            "planned_action": self.planned_action,
            "tool_called": self.tool_called,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "tool_success": self.tool_success,
            "tokens_used": self.tokens_used,
            "duration_s": self.duration_s,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "requires_approval": self.requires_approval,
            "approved": self.approved,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class ExecutionRepository:
    """
    Data access layer for execution runs and steps.

    All methods use parameterised queries (? placeholders) for safety.
    """

    def __init__(self, db_path: str | None = None):
        """
        Initialise the repository.

        Parameters
        ----------
        db_path : str, optional
            Database file path. Use ":memory:" for tests.
            Defaults to the settings-configured path.
        """
        self._conn = init_database(db_path)

    @property
    def connection(self) -> sqlite3.Connection:
        """Expose the underlying connection for advanced queries."""
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------ #
    # Execution Runs — CRUD
    # ------------------------------------------------------------------ #

    def create_run(
        self,
        user_goal: str,
        plan: Optional[list[dict]] = None,
        run_id: Optional[str] = None,
    ) -> str:
        """
        Create a new execution run.

        Parameters
        ----------
        user_goal : str
            The natural-language task description.
        plan : list[dict], optional
            The execution plan as a list of step dictionaries.
        run_id : str, optional
            Override the auto-generated UUID.

        Returns
        -------
        str
            The run_id of the created run.
        """
        if run_id is None:
            run_id = str(uuid.uuid4())[:8]

        plan_json = json.dumps(plan) if plan else None
        now = _utc_now()

        self._conn.execute(
            """
            INSERT INTO execution_runs
                (run_id, user_goal, status, plan_json, created_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (run_id, user_goal, plan_json, now),
        )
        self._conn.commit()
        return run_id

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Fetch a single run by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM execution_runs WHERE run_id = ?",
            (run_id,),
        )
        row = cursor.fetchone()
        return RunRecord(row) if row else None

    def list_runs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunRecord]:
        """
        List execution runs, optionally filtered by status.

        Returns most recent first.
        """
        if status:
            cursor = self._conn.execute(
                """
                SELECT * FROM execution_runs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (status, limit, offset),
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT * FROM execution_runs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        return [RunRecord(row) for row in cursor.fetchall()]

    def update_run_status(
        self,
        run_id: str,
        status: str,
        final_result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the status of a run, optionally setting final result or error."""
        completed_at = _utc_now() if status in ("completed", "failed", "cancelled") else None

        self._conn.execute(
            """
            UPDATE execution_runs
            SET status = ?,
                completed_at = COALESCE(?, completed_at),
                final_result = COALESCE(?, final_result),
                error_message = COALESCE(?, error_message)
            WHERE run_id = ?
            """,
            (status, completed_at, final_result, error_message, run_id),
        )
        self._conn.commit()

    def update_run_plan(self, run_id: str, plan: list[dict]) -> None:
        """Store or update the execution plan for a run."""
        plan_json = json.dumps(plan)
        self._conn.execute(
            "UPDATE execution_runs SET plan_json = ? WHERE run_id = ?",
            (plan_json, run_id),
        )
        self._conn.commit()

    def update_run_totals(self, run_id: str) -> None:
        """
        Recompute and update the aggregate totals for a run
        based on its execution_steps.
        """
        cursor = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total_steps,
                SUM(CASE WHEN tool_success = 1 THEN 1 ELSE 0 END) AS successful,
                SUM(CASE WHEN tool_success = 0 THEN 1 ELSE 0 END) AS failed,
                COALESCE(SUM(tokens_used), 0) AS total_tokens,
                COALESCE(SUM(duration_s), 0.0) AS total_duration
            FROM execution_steps
            WHERE run_id = ?
            """,
            (run_id,),
        )
        row = cursor.fetchone()
        self._conn.execute(
            """
            UPDATE execution_runs
            SET total_steps = ?,
                successful_steps = ?,
                failed_steps = ?,
                total_tokens = ?,
                total_duration = ?
            WHERE run_id = ?
            """,
            (
                row["total_steps"],
                row["successful"],
                row["failed"],
                row["total_tokens"],
                row["total_duration"],
                run_id,
            ),
        )
        self._conn.commit()

    def delete_run(self, run_id: str) -> None:
        """Delete a run and its associated steps (CASCADE)."""
        self._conn.execute(
            "DELETE FROM execution_runs WHERE run_id = ?",
            (run_id,),
        )
        self._conn.commit()

    def count_runs(self, status: Optional[str] = None) -> int:
        """Count total runs, optionally filtered by status."""
        if status:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM execution_runs WHERE status = ?",
                (status,),
            )
        else:
            cursor = self._conn.execute("SELECT COUNT(*) FROM execution_runs")
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------ #
    # Execution Steps — CRUD
    # ------------------------------------------------------------------ #

    def add_step(
        self,
        run_id: str,
        step_order: int,
        tool_called: str,
        tool_success: int,
        tool_input: Optional[str] = None,
        tool_output: Optional[str] = None,
        planned_action: Optional[str] = None,
        tokens_used: int = 0,
        duration_s: float = 0.0,
        retry_count: int = 0,
        error_message: Optional[str] = None,
        requires_approval: bool = False,
        approved: Optional[bool] = None,
    ) -> int:
        """
        Record a single execution step.

        Returns the auto-generated step ID.
        """
        now = _utc_now()
        approved_int = None if approved is None else (1 if approved else 0)

        cursor = self._conn.execute(
            """
            INSERT INTO execution_steps
                (run_id, step_order, planned_action, tool_called,
                 tool_input, tool_output, tool_success, tokens_used,
                 duration_s, retry_count, error_message,
                 requires_approval, approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id, step_order, planned_action, tool_called,
                tool_input, tool_output, tool_success, tokens_used,
                duration_s, retry_count, error_message,
                1 if requires_approval else 0, approved_int, now,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_steps(self, run_id: str) -> list[StepRecord]:
        """Fetch all steps for a run, ordered by step_order."""
        cursor = self._conn.execute(
            """
            SELECT * FROM execution_steps
            WHERE run_id = ?
            ORDER BY step_order ASC
            """,
            (run_id,),
        )
        return [StepRecord(row) for row in cursor.fetchall()]

    def get_step(self, step_id: int) -> Optional[StepRecord]:
        """Fetch a single step by its auto-increment ID."""
        cursor = self._conn.execute(
            "SELECT * FROM execution_steps WHERE id = ?",
            (step_id,),
        )
        row = cursor.fetchone()
        return StepRecord(row) if row else None

    def update_step_approval(self, step_id: int, approved: bool) -> None:
        """Record the human approval decision for a step."""
        self._conn.execute(
            "UPDATE execution_steps SET approved = ? WHERE id = ?",
            (1 if approved else 0, step_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # Analytics Queries
    # ------------------------------------------------------------------ #

    def get_tool_usage_stats(self) -> list[dict[str, Any]]:
        """
        Aggregate tool usage statistics across all runs.

        Returns a list of dicts with keys:
        tool_called, total_invocations, successes, failures, avg_tokens, avg_duration
        """
        cursor = self._conn.execute(
            """
            SELECT
                tool_called,
                COUNT(*) AS total_invocations,
                SUM(CASE WHEN tool_success = 1 THEN 1 ELSE 0 END) AS successes,
                SUM(CASE WHEN tool_success = 0 THEN 1 ELSE 0 END) AS failures,
                ROUND(AVG(tokens_used), 1) AS avg_tokens,
                ROUND(AVG(duration_s), 2) AS avg_duration
            FROM execution_steps
            GROUP BY tool_called
            ORDER BY total_invocations DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recent runs with step counts."""
        cursor = self._conn.execute(
            """
            SELECT
                r.run_id, r.user_goal, r.status, r.created_at,
                r.total_steps, r.successful_steps, r.failed_steps,
                r.total_tokens, r.total_duration
            FROM execution_runs r
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
