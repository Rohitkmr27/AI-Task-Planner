"""
Central Tool Registry and Dispatcher.

Manages tool registration, alias resolution, sensitive action detection,
and uniform execution with error trapping.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from langchain_core.tools import BaseTool

from src.agent.tools.api_caller import api_caller_tool, call_api
from src.agent.tools.base import ToolResult
from src.agent.tools.calculator import calculator_tool, run_calculator
from src.agent.tools.code_executor import code_executor_tool, execute_python_code
from src.agent.tools.data_analysis import analyze_dataset, data_analysis_tool
from src.agent.tools.email_drafter import draft_email, email_drafter_tool
from src.agent.tools.file_reader import file_reader_tool, read_file_safe
from src.agent.tools.report_writer import generate_report, report_writer_tool
from src.agent.tools.web_search import search_web, web_search_tool


# Tools requiring human confirmation before execution (HITL gate)
SENSITIVE_TOOLS = {"code_exec", "code_executor", "email_draft", "email_drafter"}

# Alias mapping to canonical tool names
TOOL_ALIASES: dict[str, str] = {
    "calc": "calc",
    "calculator": "calc",
    "math": "calc",
    "file_read": "file_read",
    "file_reader": "file_read",
    "read_file": "file_read",
    "code_exec": "code_exec",
    "code_executor": "code_exec",
    "python": "code_exec",
    "web_search": "web_search",
    "search": "web_search",
    "google": "web_search",
    "email_draft": "email_draft",
    "email_drafter": "email_draft",
    "draft_email": "email_draft",
    "api_call": "api_call",
    "api_caller": "api_call",
    "http_request": "api_call",
    "data_analysis": "data_analysis",
    "data_analyzer": "data_analysis",
    "pandas": "data_analysis",
    "report_write": "report_write",
    "report_writer": "report_write",
    "write_report": "report_write",
}

# Function mapping for direct ToolResult execution
_TOOL_RUNNERS: dict[str, Callable[..., ToolResult]] = {
    "calc": lambda **kw: run_calculator(kw.get("expression", kw.get("input", ""))),
    "file_read": lambda **kw: read_file_safe(
        file_path=kw.get("file_path", kw.get("input", "")),
        max_lines=kw.get("max_lines", 100),
    ),
    "code_exec": lambda **kw: execute_python_code(
        code=kw.get("code", kw.get("input", "")),
        timeout_s=kw.get("timeout_s"),
    ),
    "web_search": lambda **kw: search_web(
        query=kw.get("query", kw.get("input", "")),
        num_results=kw.get("num_results", 4),
    ),
    "email_draft": lambda **kw: draft_email(
        to=kw.get("to", "recipient@example.com"),
        subject=kw.get("subject", "Task Update"),
        body=kw.get("body", kw.get("input", "")),
        cc=kw.get("cc"),
    ),
    "api_call": lambda **kw: call_api(
        url=kw.get("url", kw.get("input", "")),
        method=kw.get("method", "GET"),
        payload=kw.get("payload"),
    ),
    "data_analysis": lambda **kw: analyze_dataset(
        file_path=kw.get("file_path", "dataset.csv"),
        operation=kw.get("operation", "summary"),
        group_col=kw.get("group_col"),
        agg_col=kw.get("agg_col"),
    ),
    "report_write": lambda **kw: generate_report(
        title=kw.get("title", "Executive Report"),
        executive_summary=kw.get("executive_summary", kw.get("input", "")),
        key_findings=kw.get("key_findings", []),
        recommendations=kw.get("recommendations"),
        data_table_md=kw.get("data_table_md"),
    ),
}

# LangChain BaseTool instances for LLM tool binding
LANGCHAIN_TOOLS: list[BaseTool] = [
    calculator_tool,
    file_reader_tool,
    code_executor_tool,
    web_search_tool,
    email_drafter_tool,
    api_caller_tool,
    data_analysis_tool,
    report_writer_tool,
]


def resolve_tool_name(name: str) -> str:
    """Normalize and resolve tool aliases to canonical tool name."""
    clean = name.strip().lower()
    return TOOL_ALIASES.get(clean, clean)


def is_sensitive_tool(tool_name: str) -> bool:
    """Check if the given tool requires human confirmation."""
    canonical = resolve_tool_name(tool_name)
    return canonical in SENSITIVE_TOOLS


def get_available_tools() -> list[str]:
    """Return the list of canonical tool names."""
    return list(_TOOL_RUNNERS.keys())


def execute_tool(tool_name: str, **kwargs: Any) -> ToolResult:
    """
    Execute a tool by name with arguments and return a standardized ToolResult.
    Catches all exceptions to ensure agent workflow continuity.
    """
    start_time = time.perf_counter()
    canonical = resolve_tool_name(tool_name)

    if canonical not in _TOOL_RUNNERS:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Unknown tool '{tool_name}'. Available: {get_available_tools()}",
            duration_s=0.0,
            tokens_used=5,
            requires_approval=is_sensitive_tool(tool_name),
        )

    try:
        runner = _TOOL_RUNNERS[canonical]
        res = runner(**kwargs)
        return res
    except Exception as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=canonical,
            success=False,
            output="",
            error=f"Tool execution failed: {e}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=is_sensitive_tool(canonical),
        )
