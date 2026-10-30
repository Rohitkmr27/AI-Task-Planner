"""
Pandas Data Analysis Tool.

Performs read-only exploratory and statistical data analysis on datasets
(e.g. dataset.csv, execution logs, or CSV data files). Computes summary metrics,
groupings, distributions, and returns clean Markdown tables.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd
from langchain_core.tools import tool

from src.agent.tools.base import ToolResult
from src.agent.tools.file_reader import is_path_allowed
from src.config.settings import get_settings


def _render_table(df: pd.DataFrame, index: bool = True) -> str:
    """Render DataFrame to markdown table with safe fallback to text string."""
    try:
        return df.to_markdown(index=index)
    except Exception:
        return df.to_string(index=index)


def analyze_dataset(
    file_path: str = "dataset.csv",
    operation: str = "summary",
    group_col: Optional[str] = None,
    agg_col: Optional[str] = None,
) -> ToolResult:
    """
    Perform statistical or exploratory analysis on a CSV dataset.

    Parameters
    ----------
    file_path : str
        Relative or absolute path to the CSV file.
    operation : str
        One of 'summary', 'missing', 'correlations', 'group_by', 'head'.
    group_col : str, optional
        Column name to group by (for operation='group_by').
    agg_col : str, optional
        Column to aggregate (for operation='group_by').

    Returns
    -------
    ToolResult
        Standardised tool result with analysis tables in Markdown format.
    """
    start_time = time.perf_counter()
    tool_name = "data_analysis"
    settings = get_settings()

    path_obj = Path(file_path)
    if not path_obj.is_absolute():
        path_obj = settings.project_root / file_path

    # Security check: within allowed directories
    if not is_path_allowed(path_obj, settings.allowed_dirs_list):
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Access denied: '{file_path}' is outside permitted directories.",
            duration_s=0.0,
            tokens_used=10,
            requires_approval=False,
        )

    if not path_obj.exists():
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"File not found: '{file_path}'",
            duration_s=0.0,
            tokens_used=10,
            requires_approval=False,
        )

    try:
        df = pd.read_csv(path_obj)
        op = operation.lower().strip()
        lines = [f"### Data Analysis Report: `{path_obj.name}` ({df.shape[0]} rows × {df.shape[1]} cols)\n"]

        if op in ("summary", "describe"):
            num_desc = _render_table(df.describe().round(2))
            lines.append("#### Numerical Columns Summary:")
            lines.append(num_desc)

            cat_cols = df.select_dtypes(include=["object"]).columns
            if len(cat_cols) > 0:
                lines.append("\n#### Categorical Columns Summary:")
                for col in cat_cols:
                    top_vals = df[col].value_counts().head(5).to_dict()
                    lines.append(f"- **{col}** (unique={df[col].nunique()}): {top_vals}")

        elif op in ("missing", "nulls"):
            null_counts = df.isnull().sum()
            null_pct = (null_counts / len(df) * 100).round(2)
            null_df = pd.DataFrame({"Missing Count": null_counts, "Missing %": null_pct})
            lines.append("#### Missing Values:")
            lines.append(_render_table(null_df))

        elif op in ("correlations", "corr"):
            num_df = df.select_dtypes(include=["number"])
            if num_df.shape[1] > 1:
                corr_matrix = _render_table(num_df.corr().round(3))
                lines.append("#### Pearson Correlation Matrix:")
                lines.append(corr_matrix)
            else:
                lines.append("Not enough numeric columns for correlation matrix.")

        elif op in ("group_by", "groupby"):
            if not group_col or group_col not in df.columns:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    output="",
                    error=f"group_col '{group_col}' not found in columns: {list(df.columns)}",
                    duration_s=0.0,
                    tokens_used=10,
                    requires_approval=False,
                )
            if agg_col and agg_col in df.columns:
                grouped = df.groupby(group_col)[agg_col].agg(["count", "mean", "std", "min", "max"]).round(2)
            else:
                grouped = df.groupby(group_col).size().rename("count").to_frame()
            lines.append(f"#### Grouped by `{group_col}`" + (f" (metric: `{agg_col}`):" if agg_col else ":"))
            lines.append(_render_table(grouped))

        elif op == "head":
            lines.append("#### Data Sample (First 10 Rows):")
            lines.append(_render_table(df.head(10), index=False))

        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output="",
                error=f"Unknown operation '{operation}'. Supported: summary, missing, correlations, group_by, head",
                duration_s=0.0,
                tokens_used=10,
                requires_approval=False,
            )

        output_text = "\n".join(lines)
        duration = time.perf_counter() - start_time

        return ToolResult(
            tool_name=tool_name,
            success=True,
            output=output_text,
            error=None,
            duration_s=round(duration, 4),
            tokens_used=min(3000, max(50, len(output_text) // 4)),
            requires_approval=False,
            metadata={"operation": op, "file": str(path_obj)},
        )

    except Exception as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Data analysis error: {e}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )


@tool("data_analysis")
def data_analysis_tool(file_path: str = "dataset.csv", operation: str = "summary") -> str:
    """
    Perform statistical analysis on a dataset (summary, missing, correlations, group_by, head).
    Returns formatted markdown tables.
    """
    res = analyze_dataset(file_path=file_path, operation=operation)
    if res.success:
        return res.output
    return f"Error: {res.error}"
