"""
Structured Report Writer Tool.

Generates structured, professional technical and analytical reports
formatted in clean Markdown with executive summaries, findings, tables,
and recommendations.
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.tools import tool

from src.agent.tools.base import ToolResult


def generate_report(
    title: str,
    executive_summary: str,
    key_findings: list[str] | str,
    recommendations: Optional[list[str] | str] = None,
    data_table_md: Optional[str] = None,
    author: str = "Agentic AI Task Planner",
) -> ToolResult:
    """
    Format a structured markdown report.

    Parameters
    ----------
    title : str
        Report title.
    executive_summary : str
        High-level executive overview.
    key_findings : list[str] or str
        Key insights or bullet points discovered.
    recommendations : list[str] or str, optional
        Actionable recommendations or next steps.
    data_table_md : str, optional
        Markdown data table or chart description.
    author : str
        Report author / system.

    Returns
    -------
    ToolResult
        Standardised tool result with the formatted markdown report.
    """
    start_time = time.perf_counter()
    tool_name = "report_write"

    if not title.strip():
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error="Report title cannot be empty.",
            duration_s=0.0,
            tokens_used=5,
            requires_approval=False,
        )

    # Convert findings to bullet list if passed as string or list
    if isinstance(key_findings, str):
        findings_bullets = [f"- {line.strip()}" for line in key_findings.split("\n") if line.strip()]
    else:
        findings_bullets = [f"- {f}" for f in key_findings]

    # Convert recommendations to bullet list
    recs_bullets = []
    if recommendations:
        if isinstance(recommendations, str):
            recs_bullets = [f"- {line.strip()}" for line in recommendations.split("\n") if line.strip()]
        else:
            recs_bullets = [f"- {r}" for r in recommendations]

    sections = [
        f"# {title.strip()}",
        f"\n*Author: {author}*\n",
        "## Executive Summary",
        executive_summary.strip(),
        "\n## Key Findings & Insights",
        "\n".join(findings_bullets) if findings_bullets else "- No specific findings recorded.",
    ]

    if data_table_md and data_table_md.strip():
        sections.extend([
            "\n## Supporting Data & Metrics",
            data_table_md.strip(),
        ])

    if recs_bullets:
        sections.extend([
            "\n## Strategic Recommendations & Next Steps",
            "\n".join(recs_bullets),
        ])

    sections.extend([
        "\n---",
        f"*Report prepared by {author}.*",
    ])

    report_content = "\n\n".join(sections)
    duration = time.perf_counter() - start_time

    return ToolResult(
        tool_name=tool_name,
        success=True,
        output=report_content,
        error=None,
        duration_s=round(duration, 4),
        tokens_used=min(3000, max(50, len(report_content) // 4)),
        requires_approval=False,
        metadata={"title": title, "findings_count": len(findings_bullets)},
    )


@tool("report_write")
def report_writer_tool(
    title: str,
    executive_summary: str,
    key_findings: str,
    recommendations: str = "",
) -> str:
    """
    Generate a structured technical or analytical report in Markdown.
    Includes Executive Summary, Key Findings, Supporting Data, and Recommendations.
    """
    res = generate_report(
        title=title,
        executive_summary=executive_summary,
        key_findings=key_findings,
        recommendations=recommendations if recommendations else None,
    )
    if res.success:
        return res.output
    return f"Error: {res.error}"
