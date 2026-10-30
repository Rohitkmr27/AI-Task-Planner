"""
Exploratory Data Analysis (EDA) for the Agent Execution Trace Dataset.

This module provides comprehensive analysis and visualisation functions
for the supplied dataset.csv (500 rows × 7 columns). It produces 6
distinct visualisations and a data-quality report.

Deliverable: D3 — EDA script with 3+ visualisations.

Usage:
    # As a standalone script:
    python -m src.eda.analysis

    # Programmatic access:
    from src.eda.analysis import load_dataset, run_full_eda
    df = load_dataset()
    figures = run_full_eda(df)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/CI

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Resolve the dataset path relative to the project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = _PROJECT_ROOT / "dataset.csv"

# Curated colour palette — accessible and visually distinct
TOOL_COLOURS = {
    "web_search": "#4361EE",
    "code_exec": "#7209B7",
    "calc": "#F72585",
    "api_call": "#4CC9F0",
    "file_read": "#4895EF",
    "email_draft": "#560BAD",
}

# Ordered tool names for consistent chart axes
TOOL_ORDER = ["web_search", "code_exec", "calc", "api_call", "file_read", "email_draft"]

# Directory for saving static visualisation files
OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "eda"


# ---------------------------------------------------------------------------
# Data Loading & Validation
# ---------------------------------------------------------------------------

def load_dataset(path: str | Path | None = None) -> pd.DataFrame:
    """
    Load the supplied dataset.csv and perform basic validation.

    Parameters
    ----------
    path : str or Path, optional
        Override path to the CSV file. Defaults to the project-root dataset.csv.

    Returns
    -------
    pd.DataFrame
        The loaded and validated DataFrame (unmodified from source).

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist at the given path.
    ValueError
        If the schema does not match expectations.
    """
    path = Path(path) if path else DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")

    df = pd.read_csv(path)

    # Schema validation
    expected_columns = {
        "task_id", "step_id", "tool_called",
        "tool_success", "tokens_used", "duration_s", "retry_count",
    }
    actual_columns = set(df.columns)
    if actual_columns != expected_columns:
        missing = expected_columns - actual_columns
        extra = actual_columns - expected_columns
        raise ValueError(
            f"Schema mismatch — missing: {missing}, unexpected: {extra}"
        )

    return df


def compute_summary_statistics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute key summary statistics for the dataset.

    Returns a dictionary of metrics suitable for display in a dashboard
    or inclusion in a report.
    """
    steps_per_task = df.groupby("task_id").size()

    stats = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "unique_tasks": df["task_id"].nunique(),
        "unique_tools": df["tool_called"].nunique(),
        "tool_names": sorted(df["tool_called"].unique().tolist()),
        "null_counts": df.isnull().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "overall_success_rate": round(df["tool_success"].mean(), 4),
        "total_failures": int((df["tool_success"] == 0).sum()),
        "steps_per_task": {
            "mean": round(steps_per_task.mean(), 1),
            "min": int(steps_per_task.min()),
            "max": int(steps_per_task.max()),
            "median": round(steps_per_task.median(), 1),
        },
        "tokens_used": {
            "mean": round(df["tokens_used"].mean(), 1),
            "min": int(df["tokens_used"].min()),
            "max": int(df["tokens_used"].max()),
            "std": round(df["tokens_used"].std(), 1),
        },
        "duration_s": {
            "mean": round(df["duration_s"].mean(), 2),
            "min": round(df["duration_s"].min(), 2),
            "max": round(df["duration_s"].max(), 2),
            "std": round(df["duration_s"].std(), 2),
        },
        "retry_distribution": df["retry_count"].value_counts().sort_index().to_dict(),
        "success_rate_by_tool": (
            df.groupby("tool_called")["tool_success"]
            .mean()
            .round(4)
            .to_dict()
        ),
    }
    return stats


def generate_data_quality_report(df: pd.DataFrame) -> list[dict[str, str]]:
    """
    Identify and document data-quality issues.

    Returns a list of issue dictionaries with keys:
    id, issue, severity, detail.
    """
    issues = []

    # DQ-1: step_id is globally sequential, not per-task
    if list(df["step_id"]) == list(range(1, len(df) + 1)):
        issues.append({
            "id": "DQ-1",
            "issue": "step_id is a global counter (1–500), not per-task",
            "severity": "Medium",
            "detail": (
                "A proper trace schema would have step_id reset per task_id. "
                "Within-task step ordering must be inferred from global step_id."
            ),
        })

    # DQ-2: Missing columns from brief's schema
    brief_columns = {"user_goal", "tool_input", "tool_output"}
    missing = brief_columns - set(df.columns)
    if missing:
        issues.append({
            "id": "DQ-2",
            "issue": f"Columns from project brief not in dataset: {missing}",
            "severity": "High",
            "detail": (
                "The project brief specifies user_goal, tool_input, tool_output "
                "but the supplied CSV omits them. Cannot reconstruct user intent."
            ),
        })

    # DQ-3: Column name mismatch with brief
    if "tool_success" in df.columns:
        issues.append({
            "id": "DQ-3",
            "issue": "Brief says 'success_flag' but CSV uses 'tool_success'",
            "severity": "Low",
            "detail": "Minor naming discrepancy between brief and actual schema.",
        })

    # DQ-4: No timestamps
    time_cols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower() or "at" in c.lower()]
    if not time_cols:
        issues.append({
            "id": "DQ-4",
            "issue": "No timestamp columns in dataset",
            "severity": "Low",
            "detail": (
                "Cannot perform time-series analysis or determine "
                "chronological ordering beyond step_id."
            ),
        })

    # DQ-5: Retry count vs success inconsistency
    failed_no_retry = df[(df["tool_success"] == 0) & (df["retry_count"] == 0)]
    if len(failed_no_retry) > 0:
        issues.append({
            "id": "DQ-5",
            "issue": f"{len(failed_no_retry)} steps failed with zero retries",
            "severity": "Low",
            "detail": (
                "Some tool failures were not retried, which is plausible "
                "(non-retryable errors) but worth investigating."
            ),
        })

    # DQ-6: Null check (should pass)
    null_total = df.isnull().sum().sum()
    if null_total > 0:
        issues.append({
            "id": "DQ-6",
            "issue": f"{null_total} null values found",
            "severity": "High",
            "detail": "Unexpected nulls require investigation.",
        })

    return issues


# ---------------------------------------------------------------------------
# Visualisation 1: Tool Usage Distribution (Bar Chart)
# ---------------------------------------------------------------------------

def viz_tool_usage_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart showing the frequency of each tool across all steps.

    Insight: Reveals which tools are used most/least frequently, indicating
    the agent's operational profile.
    """
    tool_counts = (
        df["tool_called"]
        .value_counts()
        .reindex(TOOL_ORDER)
        .reset_index()
    )
    tool_counts.columns = ["Tool", "Count"]

    fig = px.bar(
        tool_counts,
        x="Count",
        y="Tool",
        orientation="h",
        color="Tool",
        color_discrete_map=TOOL_COLOURS,
        title="Tool Usage Distribution Across All Steps",
        labels={"Count": "Number of Invocations", "Tool": ""},
        text="Count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        xaxis_title="Number of Invocations",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        margin=dict(l=10, r=40, t=50, b=30),
        height=400,
    )
    return fig


# ---------------------------------------------------------------------------
# Visualisation 2: Success Rate by Tool (Grouped Bar)
# ---------------------------------------------------------------------------

def viz_success_rate_by_tool(df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar chart showing success vs failure counts per tool.

    Insight: Identifies which tools are most/least reliable, informing
    error-handling priorities.
    """
    grouped = (
        df.groupby(["tool_called", "tool_success"])
        .size()
        .reset_index(name="Count")
    )
    grouped["Outcome"] = grouped["tool_success"].map({1: "Success", 0: "Failure"})

    fig = px.bar(
        grouped,
        x="tool_called",
        y="Count",
        color="Outcome",
        barmode="group",
        color_discrete_map={"Success": "#06D6A0", "Failure": "#EF476F"},
        title="Success vs Failure Count by Tool",
        labels={"tool_called": "Tool", "Count": "Number of Steps"},
        category_orders={"tool_called": TOOL_ORDER},
        text="Count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        margin=dict(l=10, r=10, t=50, b=30),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


# ---------------------------------------------------------------------------
# Visualisation 3: Token Usage Distribution (Histogram + Box)
# ---------------------------------------------------------------------------

def viz_token_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Combined histogram and box plot of tokens_used, coloured by tool.

    Insight: Shows the overall token consumption profile and whether
    certain tools are more token-heavy.
    """
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.75, 0.25],
        shared_xaxes=True,
        vertical_spacing=0.05,
    )

    # Histogram
    for tool in TOOL_ORDER:
        subset = df[df["tool_called"] == tool]
        fig.add_trace(
            go.Histogram(
                x=subset["tokens_used"],
                name=tool,
                marker_color=TOOL_COLOURS[tool],
                opacity=0.7,
                nbinsx=25,
            ),
            row=1, col=1,
        )

    # Box plot
    fig.add_trace(
        go.Box(
            x=df["tokens_used"],
            name="All Tools",
            marker_color="#4361EE",
            boxmean=True,
        ),
        row=2, col=1,
    )

    fig.update_layout(
        title="Token Usage Distribution by Tool",
        barmode="stack",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        height=500,
        margin=dict(l=10, r=10, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    fig.update_xaxes(title_text="Tokens Used", row=2, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    return fig


# ---------------------------------------------------------------------------
# Visualisation 4: Duration by Tool (Box Plot)
# ---------------------------------------------------------------------------

def viz_duration_by_tool(df: pd.DataFrame) -> go.Figure:
    """
    Box plot of execution duration per tool.

    Insight: Reveals execution-time variability and outliers per tool,
    useful for timeout configuration.
    """
    fig = px.box(
        df,
        x="tool_called",
        y="duration_s",
        color="tool_called",
        color_discrete_map=TOOL_COLOURS,
        category_orders={"tool_called": TOOL_ORDER},
        title="Execution Duration Distribution by Tool",
        labels={"tool_called": "Tool", "duration_s": "Duration (seconds)"},
        points="outliers",
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        height=420,
        margin=dict(l=10, r=10, t=50, b=30),
    )
    return fig


# ---------------------------------------------------------------------------
# Visualisation 5: Retry Analysis (Stacked Bar)
# ---------------------------------------------------------------------------

def viz_retry_analysis(df: pd.DataFrame) -> go.Figure:
    """
    Stacked bar chart of retry count distribution per tool.

    Insight: Shows which tools require the most retries, indicating
    reliability issues worth investigating.
    """
    retry_data = (
        df.groupby(["tool_called", "retry_count"])
        .size()
        .reset_index(name="Count")
    )
    retry_data["retry_count"] = retry_data["retry_count"].astype(str) + " retries"

    fig = px.bar(
        retry_data,
        x="tool_called",
        y="Count",
        color="retry_count",
        barmode="stack",
        color_discrete_sequence=["#06D6A0", "#FFD166", "#EF476F"],
        title="Retry Count Distribution by Tool",
        labels={"tool_called": "Tool", "Count": "Number of Steps", "retry_count": "Retries"},
        category_orders={"tool_called": TOOL_ORDER},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        height=420,
        margin=dict(l=10, r=10, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


# ---------------------------------------------------------------------------
# Visualisation 6: Steps per Task Distribution (Histogram)
# ---------------------------------------------------------------------------

def viz_steps_per_task(df: pd.DataFrame) -> go.Figure:
    """
    Histogram of the number of execution steps per task.

    Insight: Reveals task complexity distribution — how many steps
    the agent typically needs to complete a task.
    """
    steps = df.groupby("task_id").size().reset_index(name="Steps")

    fig = px.histogram(
        steps,
        x="Steps",
        nbins=10,
        title="Distribution of Steps per Task",
        labels={"Steps": "Number of Steps per Task", "count": "Number of Tasks"},
        color_discrete_sequence=["#4361EE"],
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        height=400,
        margin=dict(l=10, r=10, t=50, b=30),
        bargap=0.1,
    )
    fig.update_yaxes(title_text="Number of Tasks")
    return fig


# ---------------------------------------------------------------------------
# Matplotlib Visualisation: Correlation Heatmap (Static)
# ---------------------------------------------------------------------------

def viz_correlation_heatmap(df: pd.DataFrame) -> plt.Figure:
    """
    Matplotlib/Seaborn heatmap of correlations between numeric columns.

    Insight: Reveals relationships (or lack thereof) between token usage,
    duration, retry count, and success. Useful for identifying whether
    higher token usage correlates with success or longer duration.
    """
    numeric_cols = ["tool_success", "tokens_used", "duration_s", "retry_count"]
    corr = df[numeric_cols].corr()

    fig, ax = plt.subplots(figsize=(7, 5.5))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".3f",
        cmap="RdYlBu_r",
        center=0,
        square=True,
        linewidths=0.5,
        ax=ax,
        vmin=-1, vmax=1,
        cbar_kws={"label": "Pearson Correlation", "shrink": 0.8},
    )
    ax.set_title("Correlation Matrix — Numeric Features", fontsize=14, pad=12)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Run All Visualisations
# ---------------------------------------------------------------------------

def run_full_eda(
    df: pd.DataFrame,
    save_to_disk: bool = False,
) -> dict[str, Any]:
    """
    Execute the complete EDA pipeline: compute statistics, generate
    data-quality report, and create all visualisations.

    Parameters
    ----------
    df : pd.DataFrame
        The loaded dataset.
    save_to_disk : bool, default False
        If True, save figures to the outputs/eda/ directory.

    Returns
    -------
    dict with keys:
        - "statistics": dict of summary statistics
        - "data_quality": list of issue dicts
        - "figures_plotly": dict[str, go.Figure]
        - "figures_matplotlib": dict[str, plt.Figure]
    """
    # Compute statistics
    stats = compute_summary_statistics(df)
    dq_issues = generate_data_quality_report(df)

    # Generate Plotly figures
    plotly_figs = {
        "tool_usage_distribution": viz_tool_usage_distribution(df),
        "success_rate_by_tool": viz_success_rate_by_tool(df),
        "token_distribution": viz_token_distribution(df),
        "duration_by_tool": viz_duration_by_tool(df),
        "retry_analysis": viz_retry_analysis(df),
        "steps_per_task": viz_steps_per_task(df),
    }

    # Generate Matplotlib figures
    mpl_figs = {
        "correlation_heatmap": viz_correlation_heatmap(df),
    }

    # Optionally save to disk
    if save_to_disk:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for name, fig in plotly_figs.items():
            fig.write_html(OUTPUT_DIR / f"{name}.html")
            print(f"  Saved: {OUTPUT_DIR / f'{name}.html'}")

        for name, fig in mpl_figs.items():
            fig.savefig(OUTPUT_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
            print(f"  Saved: {OUTPUT_DIR / f'{name}.png'}")

    return {
        "statistics": stats,
        "data_quality": dq_issues,
        "figures_plotly": plotly_figs,
        "figures_matplotlib": mpl_figs,
    }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    """Run EDA from the command line and print results."""
    print("=" * 65)
    print("  Agentic AI Task Planner -- Exploratory Data Analysis")
    print("=" * 65)

    # Load
    print(f"\n[DATA]  Loading dataset from: {DATASET_PATH}")
    df = load_dataset()
    print(f"    Shape: {df.shape[0]} rows x {df.shape[1]} columns")

    # Statistics
    print("\n[STATS]  Summary Statistics")
    print("-" * 45)
    stats = compute_summary_statistics(df)
    print(f"    Unique tasks:          {stats['unique_tasks']}")
    print(f"    Unique tools:          {stats['unique_tools']} ({', '.join(stats['tool_names'])})")
    print(f"    Overall success rate:  {stats['overall_success_rate']:.1%}")
    print(f"    Total failures:        {stats['total_failures']}")
    print(f"    Steps per task:        mean={stats['steps_per_task']['mean']}, "
          f"min={stats['steps_per_task']['min']}, max={stats['steps_per_task']['max']}")
    print(f"    Tokens used:           mean={stats['tokens_used']['mean']:.0f}, "
          f"range=[{stats['tokens_used']['min']}, {stats['tokens_used']['max']}]")
    print(f"    Duration (s):          mean={stats['duration_s']['mean']:.1f}, "
          f"range=[{stats['duration_s']['min']}, {stats['duration_s']['max']}]")
    print(f"    Retry distribution:    {stats['retry_distribution']}")
    print(f"    Null values:           {sum(stats['null_counts'].values())} total")
    print(f"    Duplicate rows:        {stats['duplicate_rows']}")

    print("\n    Success Rate by Tool:")
    for tool, rate in sorted(stats["success_rate_by_tool"].items()):
        filled = int(rate * 30)
        bar = "#" * filled + "-" * (30 - filled)
        print(f"      {tool:14s}  [{bar}]  {rate:.1%}")

    # Data Quality
    print("\n[WARN]  Data Quality Issues")
    print("-" * 45)
    dq_issues = generate_data_quality_report(df)
    if not dq_issues:
        print("    No issues found.")
    for issue in dq_issues:
        print(f"    [{issue['id']}] ({issue['severity']}) {issue['issue']}")
        print(f"         {issue['detail']}")

    # Generate and save visualisations
    print("\n[CHARTS]  Generating Visualisations...")
    results = run_full_eda(df, save_to_disk=True)
    print(f"\n[DONE]  EDA complete -- {len(results['figures_plotly'])} Plotly + "
          f"{len(results['figures_matplotlib'])} Matplotlib figures generated.")
    print(f"    Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
