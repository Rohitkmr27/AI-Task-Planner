"""
Shared pytest fixtures for the Agentic AI Task Planner test suite.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Path Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def dataset_path(project_root: Path) -> Path:
    """Return the path to the original dataset.csv."""
    return project_root / "dataset.csv"


# ---------------------------------------------------------------------------
# Data Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df() -> pd.DataFrame:
    """
    A small, representative DataFrame for unit tests.

    Contains 10 rows covering all 6 tool types, both success and failure,
    and different retry counts. Avoids hitting the real dataset.
    """
    return pd.DataFrame({
        "task_id": ["T001", "T001", "T001", "T002", "T002",
                    "T003", "T003", "T004", "T004", "T005"],
        "step_id": list(range(1, 11)),
        "tool_called": [
            "web_search", "calc", "email_draft",
            "code_exec", "api_call",
            "file_read", "web_search",
            "calc", "code_exec",
            "email_draft",
        ],
        "tool_success": [1, 1, 0, 1, 1, 1, 0, 1, 1, 1],
        "tokens_used": [2000, 500, 1500, 3000, 1200, 800, 2500, 1000, 3500, 600],
        "duration_s": [10.5, 2.1, 8.3, 15.2, 5.4, 3.1, 12.7, 1.8, 20.0, 4.5],
        "retry_count": [0, 0, 1, 0, 0, 0, 2, 1, 0, 0],
    })


@pytest.fixture
def real_df(dataset_path: Path) -> pd.DataFrame:
    """
    Load the real dataset.csv. Skips the test if the file is missing.
    """
    if not dataset_path.exists():
        pytest.skip(f"Dataset not found at {dataset_path}")
    return pd.read_csv(dataset_path)
