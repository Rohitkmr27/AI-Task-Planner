"""
SQLite database schema and table creation for runtime execution logs.

This module defines the schema for the agent's execution trace database,
which is SEPARATE from the supplied dataset.csv. The original dataset
is never modified.

Tables:
    execution_runs  — One row per agent task execution
    execution_steps — One row per tool invocation within a run
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.config.settings import get_settings


# ---------------------------------------------------------------------------
# Schema Definitions (DDL)
# ---------------------------------------------------------------------------

CREATE_EXECUTION_RUNS = """
CREATE TABLE IF NOT EXISTS execution_runs (
    run_id          TEXT PRIMARY KEY,
    user_goal       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'planning', 'running', 'completed', 'failed', 'cancelled')),
    plan_json       TEXT,
    created_at      TEXT NOT NULL,
    completed_at    TEXT,
    total_tokens    INTEGER DEFAULT 0,
    total_duration  REAL DEFAULT 0.0,
    total_steps     INTEGER DEFAULT 0,
    successful_steps INTEGER DEFAULT 0,
    failed_steps    INTEGER DEFAULT 0,
    final_result    TEXT,
    error_message   TEXT
);
"""

CREATE_EXECUTION_STEPS = """
CREATE TABLE IF NOT EXISTS execution_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    step_order      INTEGER NOT NULL,
    planned_action  TEXT,
    tool_called     TEXT NOT NULL,
    tool_input      TEXT,
    tool_output     TEXT,
    tool_success    INTEGER NOT NULL DEFAULT 0
                    CHECK(tool_success IN (0, 1)),
    tokens_used     INTEGER DEFAULT 0,
    duration_s      REAL DEFAULT 0.0,
    retry_count     INTEGER DEFAULT 0,
    error_message   TEXT,
    requires_approval INTEGER DEFAULT 0,
    approved        INTEGER,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES execution_runs(run_id)
        ON DELETE CASCADE
);
"""

CREATE_STEP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_steps_run_id
ON execution_steps(run_id);
"""

CREATE_RUNS_STATUS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_runs_status
ON execution_runs(status);
"""

ALL_DDL = [
    CREATE_EXECUTION_RUNS,
    CREATE_EXECUTION_STEPS,
    CREATE_STEP_INDEX,
    CREATE_RUNS_STATUS_INDEX,
]


# ---------------------------------------------------------------------------
# Database Initialisation
# ---------------------------------------------------------------------------

def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Create a SQLite connection with recommended settings.

    Parameters
    ----------
    db_path : str or Path, optional
        Path to the database file. Defaults to settings.database_path.
        Use ":memory:" for in-memory testing databases.

    Returns
    -------
    sqlite3.Connection
        A configured connection with WAL mode, foreign keys enabled,
        and Row factory for dict-like access.
    """
    if db_path is None:
        db_path = get_settings().database_path

    db_path = str(db_path)

    # Ensure parent directory exists (unless in-memory)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Initialise the database: create tables if they don't exist.

    Parameters
    ----------
    db_path : str or Path, optional
        Override the database path. Defaults to settings.database_path.

    Returns
    -------
    sqlite3.Connection
        The initialised database connection.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for ddl in ALL_DDL:
        cursor.execute(ddl)
    conn.commit()
    return conn


def reset_database(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Drop and recreate all tables. USE WITH CAUTION — destroys all data.

    This is intended for testing and development only.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS execution_steps")
    cursor.execute("DROP TABLE IF EXISTS execution_runs")
    for ddl in ALL_DDL:
        cursor.execute(ddl)
    conn.commit()
    return conn
