"""
Tests for the EDA analysis module.

Validates data loading, summary statistics, data-quality detection,
and visualisation generation — all without modifying dataset.csv.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.eda.analysis import (
    compute_summary_statistics,
    generate_data_quality_report,
    load_dataset,
    run_full_eda,
    viz_correlation_heatmap,
    viz_duration_by_tool,
    viz_retry_analysis,
    viz_steps_per_task,
    viz_success_rate_by_tool,
    viz_token_distribution,
    viz_tool_usage_distribution,
)


# =========================================================================
# Data Loading Tests
# =========================================================================

class TestLoadDataset:
    """Tests for the load_dataset function."""

    def test_load_real_dataset(self, dataset_path: Path):
        """Loading the real dataset.csv produces a DataFrame with expected shape."""
        df = load_dataset(dataset_path)
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (500, 7)

    def test_load_real_dataset_columns(self, dataset_path: Path):
        """The real dataset has exactly the 7 expected columns."""
        df = load_dataset(dataset_path)
        expected = {"task_id", "step_id", "tool_called",
                    "tool_success", "tokens_used", "duration_s", "retry_count"}
        assert set(df.columns) == expected

    def test_load_missing_file_raises(self, tmp_path: Path):
        """Loading from a non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nonexistent.csv")

    def test_load_wrong_schema_raises(self, tmp_path: Path):
        """Loading a CSV with wrong columns raises ValueError."""
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("col_a,col_b\n1,2\n")
        with pytest.raises(ValueError, match="Schema mismatch"):
            load_dataset(bad_csv)

    def test_dataset_has_no_nulls(self, dataset_path: Path):
        """The real dataset contains zero null values."""
        df = load_dataset(dataset_path)
        assert df.isnull().sum().sum() == 0

    def test_dataset_has_no_duplicates(self, dataset_path: Path):
        """The real dataset contains zero duplicate rows."""
        df = load_dataset(dataset_path)
        assert df.duplicated().sum() == 0

    def test_dataset_not_modified_on_load(self, dataset_path: Path):
        """Loading the dataset does not write to the CSV file."""
        mtime_before = dataset_path.stat().st_mtime
        _ = load_dataset(dataset_path)
        mtime_after = dataset_path.stat().st_mtime
        assert mtime_before == mtime_after, "dataset.csv was modified during load!"


# =========================================================================
# Summary Statistics Tests
# =========================================================================

class TestSummaryStatistics:
    """Tests for compute_summary_statistics."""

    def test_returns_dict(self, sample_df: pd.DataFrame):
        """Summary statistics returns a dictionary."""
        stats = compute_summary_statistics(sample_df)
        assert isinstance(stats, dict)

    def test_expected_keys(self, sample_df: pd.DataFrame):
        """The returned dict contains all expected keys."""
        stats = compute_summary_statistics(sample_df)
        expected_keys = {
            "total_rows", "total_columns", "unique_tasks", "unique_tools",
            "tool_names", "null_counts", "duplicate_rows",
            "overall_success_rate", "total_failures", "steps_per_task",
            "tokens_used", "duration_s", "retry_distribution",
            "success_rate_by_tool",
        }
        assert expected_keys.issubset(stats.keys())

    def test_sample_row_count(self, sample_df: pd.DataFrame):
        """Row count matches the sample DataFrame."""
        stats = compute_summary_statistics(sample_df)
        assert stats["total_rows"] == 10

    def test_sample_unique_tasks(self, sample_df: pd.DataFrame):
        """Unique task count is correct for sample data."""
        stats = compute_summary_statistics(sample_df)
        assert stats["unique_tasks"] == 5

    def test_sample_success_rate(self, sample_df: pd.DataFrame):
        """Success rate is correctly computed for sample data (8/10 = 0.8)."""
        stats = compute_summary_statistics(sample_df)
        assert stats["overall_success_rate"] == 0.8

    def test_sample_failure_count(self, sample_df: pd.DataFrame):
        """Failure count is correct (2 failures in sample)."""
        stats = compute_summary_statistics(sample_df)
        assert stats["total_failures"] == 2

    def test_real_dataset_stats(self, dataset_path: Path):
        """Validate key statistics against known values from the real dataset."""
        df = load_dataset(dataset_path)
        stats = compute_summary_statistics(df)
        assert stats["total_rows"] == 500
        assert stats["total_columns"] == 7
        assert stats["unique_tasks"] == 100
        assert stats["unique_tools"] == 6
        assert stats["overall_success_rate"] == 0.892
        assert stats["total_failures"] == 54
        assert stats["duplicate_rows"] == 0


# =========================================================================
# Data Quality Tests
# =========================================================================

class TestDataQuality:
    """Tests for generate_data_quality_report."""

    def test_returns_list(self, sample_df: pd.DataFrame):
        """Data quality report returns a list."""
        issues = generate_data_quality_report(sample_df)
        assert isinstance(issues, list)

    def test_issues_have_required_keys(self, sample_df: pd.DataFrame):
        """Each issue has id, issue, severity, and detail keys."""
        issues = generate_data_quality_report(sample_df)
        for issue in issues:
            assert "id" in issue
            assert "issue" in issue
            assert "severity" in issue
            assert "detail" in issue

    def test_real_dataset_detects_global_stepid(self, dataset_path: Path):
        """DQ-1 (global step_id) is detected on the real dataset."""
        df = load_dataset(dataset_path)
        issues = generate_data_quality_report(df)
        issue_ids = [i["id"] for i in issues]
        assert "DQ-1" in issue_ids

    def test_real_dataset_detects_missing_columns(self, dataset_path: Path):
        """DQ-2 (missing columns from brief) is detected."""
        df = load_dataset(dataset_path)
        issues = generate_data_quality_report(df)
        issue_ids = [i["id"] for i in issues]
        assert "DQ-2" in issue_ids


# =========================================================================
# Visualisation Tests
# =========================================================================

class TestVisualisations:
    """Tests that each visualisation function returns the correct figure type."""

    def test_tool_usage_returns_plotly(self, sample_df: pd.DataFrame):
        fig = viz_tool_usage_distribution(sample_df)
        assert isinstance(fig, go.Figure)

    def test_success_rate_returns_plotly(self, sample_df: pd.DataFrame):
        fig = viz_success_rate_by_tool(sample_df)
        assert isinstance(fig, go.Figure)

    def test_token_distribution_returns_plotly(self, sample_df: pd.DataFrame):
        fig = viz_token_distribution(sample_df)
        assert isinstance(fig, go.Figure)

    def test_duration_by_tool_returns_plotly(self, sample_df: pd.DataFrame):
        fig = viz_duration_by_tool(sample_df)
        assert isinstance(fig, go.Figure)

    def test_retry_analysis_returns_plotly(self, sample_df: pd.DataFrame):
        fig = viz_retry_analysis(sample_df)
        assert isinstance(fig, go.Figure)

    def test_steps_per_task_returns_plotly(self, sample_df: pd.DataFrame):
        fig = viz_steps_per_task(sample_df)
        assert isinstance(fig, go.Figure)

    def test_correlation_heatmap_returns_matplotlib(self, sample_df: pd.DataFrame):
        fig = viz_correlation_heatmap(sample_df)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)  # Clean up


# =========================================================================
# Full EDA Pipeline Test
# =========================================================================

class TestRunFullEDA:
    """Tests for the run_full_eda orchestrator."""

    def test_returns_expected_structure(self, sample_df: pd.DataFrame):
        """run_full_eda returns a dict with statistics, quality, and figures."""
        results = run_full_eda(sample_df, save_to_disk=False)
        assert "statistics" in results
        assert "data_quality" in results
        assert "figures_plotly" in results
        assert "figures_matplotlib" in results

    def test_produces_six_plotly_figures(self, sample_df: pd.DataFrame):
        """The pipeline produces exactly 6 Plotly figures."""
        results = run_full_eda(sample_df, save_to_disk=False)
        assert len(results["figures_plotly"]) == 6

    def test_produces_one_matplotlib_figure(self, sample_df: pd.DataFrame):
        """The pipeline produces exactly 1 Matplotlib figure."""
        results = run_full_eda(sample_df, save_to_disk=False)
        assert len(results["figures_matplotlib"]) == 1
        # Clean up
        for fig in results["figures_matplotlib"].values():
            plt.close(fig)

    def test_save_to_disk(self, sample_df: pd.DataFrame, tmp_path: Path, monkeypatch):
        """Saving to disk creates HTML and PNG files."""
        import src.eda.analysis as analysis_module
        monkeypatch.setattr(analysis_module, "OUTPUT_DIR", tmp_path)
        results = run_full_eda(sample_df, save_to_disk=True)

        html_files = list(tmp_path.glob("*.html"))
        png_files = list(tmp_path.glob("*.png"))
        assert len(html_files) == 6
        assert len(png_files) == 1

        # Clean up matplotlib figures
        for fig in results["figures_matplotlib"].values():
            plt.close(fig)
