"""
Tools subpackage for the Agentic AI Task Planner.
"""

from src.agent.tools.api_caller import api_caller_tool, call_api
from src.agent.tools.base import ToolResult
from src.agent.tools.calculator import calculator_tool, evaluate_expression, run_calculator
from src.agent.tools.code_executor import code_executor_tool, execute_python_code
from src.agent.tools.data_analysis import analyze_dataset, data_analysis_tool
from src.agent.tools.email_drafter import draft_email, email_drafter_tool
from src.agent.tools.file_reader import file_reader_tool, read_file_safe
from src.agent.tools.registry import (
    LANGCHAIN_TOOLS,
    SENSITIVE_TOOLS,
    execute_tool,
    get_available_tools,
    is_sensitive_tool,
    resolve_tool_name,
)
from src.agent.tools.report_writer import generate_report, report_writer_tool
from src.agent.tools.web_search import search_web, web_search_tool

__all__ = [
    "ToolResult",
    "run_calculator",
    "evaluate_expression",
    "calculator_tool",
    "read_file_safe",
    "file_reader_tool",
    "execute_python_code",
    "code_executor_tool",
    "search_web",
    "web_search_tool",
    "draft_email",
    "email_drafter_tool",
    "call_api",
    "api_caller_tool",
    "analyze_dataset",
    "data_analysis_tool",
    "generate_report",
    "report_writer_tool",
    "LANGCHAIN_TOOLS",
    "SENSITIVE_TOOLS",
    "execute_tool",
    "get_available_tools",
    "is_sensitive_tool",
    "resolve_tool_name",
]
