"""
Comprehensive unit tests for the agent tools (Phase 2).

Tests:
1. Calculator: arithmetic, math functions, AST safety against injection/eval.
2. File Reader: CSV, JSON, TXT parsing, directory traversal prevention.
3. Code Executor: subprocess execution, timeout handling, sensitive approval flag.
4. Web Search: query parsing, simulated search results, structure.
5. Email Drafter: watermarking, draft-only guarantee, sensitive approval flag.
6. API Caller: URL validation, error handling.
7. Data Analysis: summary, missing, correlations, groupby.
8. Report Writer: structured markdown generation.
9. Registry: tool resolution, execution dispatcher, sensitive tool detection.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.agent.tools.api_caller import call_api
from src.agent.tools.calculator import evaluate_expression, run_calculator
from src.agent.tools.code_executor import execute_python_code
from src.agent.tools.data_analysis import analyze_dataset
from src.agent.tools.email_drafter import DRAFT_WATERMARK, draft_email
from src.agent.tools.file_reader import is_path_allowed, read_file_safe
from src.agent.tools.registry import (
    LANGCHAIN_TOOLS,
    execute_tool,
    get_available_tools,
    is_sensitive_tool,
    resolve_tool_name,
)
from src.agent.tools.report_writer import generate_report
from src.agent.tools.web_search import search_web


# ---------------------------------------------------------------------------
# 1. Calculator Tests
# ---------------------------------------------------------------------------

class TestCalculatorTool:
    """Test safe AST-based mathematical evaluation."""

    def test_basic_arithmetic(self):
        assert evaluate_expression("2 + 2") == 4
        assert evaluate_expression("10 - 4 * 2") == 2
        assert evaluate_expression("(10 - 4) * 2") == 12
        assert evaluate_expression("15 / 3") == 5.0
        assert evaluate_expression("7 // 2") == 3
        assert evaluate_expression("7 % 3") == 1
        assert evaluate_expression("2 ** 8") == 256

    def test_math_functions_and_constants(self):
        assert evaluate_expression("sqrt(144)") == 12.0
        assert evaluate_expression("abs(-42)") == 42
        assert pytest.approx(evaluate_expression("3.14 * 5**2"), 0.01) == 78.5
        assert evaluate_expression("round(3.14159, 2)") == 3.14
        assert evaluate_expression("factorial(5)") == 120
        assert pytest.approx(evaluate_expression("sin(0)"), 0.001) == 0.0

    def test_rejection_of_arbitrary_code_execution(self):
        """Calculator must reject imports, exec, and system commands."""
        with pytest.raises(ValueError):
            evaluate_expression("import os; os.system('ls')")

        with pytest.raises(ValueError):
            evaluate_expression("__import__('os').system('ls')")

        with pytest.raises(ValueError):
            evaluate_expression("open('secret.txt')")

        with pytest.raises(ValueError):
            evaluate_expression("eval('2+2')")

    def test_run_calculator_tool_result(self):
        res = run_calculator("sqrt(144) + 10")
        assert res.success is True
        assert res.output == "22.0"
        assert res.error is None
        assert res.requires_approval is False

        bad_res = run_calculator("invalid syntax ++ *")
        assert bad_res.success is False
        assert "error" in (bad_res.error or "").lower()


# ---------------------------------------------------------------------------
# 2. File Reader Tests
# ---------------------------------------------------------------------------

class TestFileReaderTool:
    """Test safe file reading and directory traversal protection."""

    def test_read_csv(self, project_root: Path):
        res = read_file_safe("dataset.csv", max_lines=5)
        assert res.success is True
        assert "500 rows" in res.output
        assert "task_id" in res.output

    def test_read_data_dictionary(self, project_root: Path):
        res = read_file_safe("data_dictionary.csv", max_lines=10)
        assert res.success is True
        assert "column_name" in res.output

    def test_directory_traversal_blocked(self, project_root: Path):
        """Attempts to escape project directory must fail."""
        res = read_file_safe("../../Windows/System32/drivers/etc/hosts")
        assert res.success is False
        assert "Access denied" in (res.error or "")

    def test_nonexistent_file(self):
        res = read_file_safe("nonexistent_file_xyz.csv")
        assert res.success is False
        assert "File not found" in (res.error or "")

    def test_unsupported_extension_blocked(self, tmp_path: Path):
        binary_file = tmp_path / "danger.exe"
        binary_file.write_bytes(b"\x00\x01\x02")
        res = read_file_safe(str(binary_file), allowed_dirs=[tmp_path])
        assert res.success is False
        assert "not permitted" in (res.error or "")


# ---------------------------------------------------------------------------
# 3. Code Executor Tests
# ---------------------------------------------------------------------------

class TestCodeExecutorTool:
    """Test subprocess code execution, timeout, and sensitive approval gate."""

    def test_successful_execution(self):
        code = "print('Hello from Agent')\nx = 10 * 5\nprint(f'Computed: {x}')"
        res = execute_python_code(code)
        assert res.success is True
        assert "Hello from Agent" in res.output
        assert "Computed: 50" in res.output
        assert res.requires_approval is True  # HITL flag

    def test_syntax_or_runtime_error_captured(self):
        code = "print(10 / 0)"
        res = execute_python_code(code)
        assert res.success is False
        assert "ZeroDivisionError" in (res.error or "")
        assert res.requires_approval is True

    def test_timeout_enforcement(self):
        code = "import time\ntime.sleep(5)"
        res = execute_python_code(code, timeout_s=1)
        assert res.success is False
        assert "timed out" in (res.error or "")

    def test_empty_code_rejected(self):
        res = execute_python_code("   ")
        assert res.success is False
        assert "Empty code" in (res.error or "")


# ---------------------------------------------------------------------------
# 4. Web Search Tests
# ---------------------------------------------------------------------------

class TestWebSearchTool:
    """Test web research with offline simulation fallback."""

    def test_search_ai_agents(self):
        res = search_web("LangGraph agent planning")
        assert res.success is True
        assert len(res.output) > 20
        assert "LangGraph" in res.output
        assert res.requires_approval is False

    def test_search_eda(self):
        res = search_web("exploratory data analysis pandas")
        assert res.success is True
        assert "pandas" in res.output.lower()

    def test_empty_query(self):
        res = search_web("")
        assert res.success is False
        assert "cannot be empty" in (res.error or "")


# ---------------------------------------------------------------------------
# 5. Email Drafter Tests
# ---------------------------------------------------------------------------

class TestEmailDrafterTool:
    """Test email drafting, watermarking, and sensitive approval gate."""

    def test_draft_email_content_and_watermark(self):
        res = draft_email(
            to="manager@company.com",
            subject="Project Milestone Completed",
            body="Phase 1 and Phase 2 implementations are complete.",
            cc="team@company.com",
        )
        assert res.success is True
        assert DRAFT_WATERMARK in res.output
        assert "manager@company.com" in res.output
        assert "team@company.com" in res.output
        assert "Project Milestone Completed" in res.output
        assert "Phase 1 and Phase 2" in res.output
        assert res.requires_approval is True  # SENSITIVE: requires human approval

    def test_missing_fields_validation(self):
        res = draft_email(to="", subject="Test", body="Body")
        assert res.success is False
        assert "Recipient" in (res.error or "")

        res2 = draft_email(to="user@test.com", subject="", body="Body")
        assert res2.success is False
        assert "Subject" in (res2.error or "")


# ---------------------------------------------------------------------------
# 6. API Caller Tests
# ---------------------------------------------------------------------------

class TestApiCallerTool:
    """Test HTTP API caller tool."""

    def test_invalid_url_rejected(self):
        res = call_api("ftp://not-supported.com")
        assert res.success is False
        assert "Invalid URL" in (res.error or "")

    def test_unreachable_endpoint_graceful_failure(self):
        res = call_api("http://localhost:59999/nonexistent-endpoint-xyz", timeout_s=1)
        assert res.success is False
        assert res.error is not None


# ---------------------------------------------------------------------------
# 7. Data Analysis Tests
# ---------------------------------------------------------------------------

class TestDataAnalysisTool:
    """Test Pandas exploratory and statistical data analysis tool."""

    def test_summary_operation(self):
        res = analyze_dataset(file_path="dataset.csv", operation="summary")
        assert res.success is True
        assert "tokens_used" in res.output
        assert "Numerical Columns Summary" in res.output

    def test_missing_operation(self):
        res = analyze_dataset(file_path="dataset.csv", operation="missing")
        assert res.success is True
        assert "Missing Count" in res.output

    def test_correlations_operation(self):
        res = analyze_dataset(file_path="dataset.csv", operation="correlations")
        assert res.success is True
        assert "Pearson Correlation Matrix" in res.output

    def test_groupby_operation(self):
        res = analyze_dataset(
            file_path="dataset.csv",
            operation="group_by",
            group_col="tool_called",
            agg_col="duration_s",
        )
        assert res.success is True
        assert "calc" in res.output
        assert "mean" in res.output

    def test_invalid_operation(self):
        res = analyze_dataset(file_path="dataset.csv", operation="unsupported_op")
        assert res.success is False
        assert "Unknown operation" in (res.error or "")


# ---------------------------------------------------------------------------
# 8. Report Writer Tests
# ---------------------------------------------------------------------------

class TestReportWriterTool:
    """Test structured markdown report generation."""

    def test_generate_report(self):
        res = generate_report(
            title="Q3 Agent Performance Report",
            executive_summary="The AI task planner achieved an 89.2% overall success rate across 500 execution steps.",
            key_findings=[
                "Top tool by volume was calculator (91 invocations).",
                "Average duration across tools was 15.1 seconds.",
            ],
            recommendations=[
                "Add caching for recurrent mathematical computations.",
                "Implement fallback routes on web search timeouts.",
            ],
        )
        assert res.success is True
        assert "# Q3 Agent Performance Report" in res.output
        assert "Executive Summary" in res.output
        assert "Top tool by volume" in res.output
        assert "Strategic Recommendations" in res.output


# ---------------------------------------------------------------------------
# 9. Tool Registry & Dispatcher Tests
# ---------------------------------------------------------------------------

class TestToolRegistry:
    """Test registry alias resolution, execution dispatcher, and sensitive flags."""

    def test_resolve_tool_aliases(self):
        assert resolve_tool_name("calc") == "calc"
        assert resolve_tool_name("calculator") == "calc"
        assert resolve_tool_name("python") == "code_exec"
        assert resolve_tool_name("file_reader") == "file_read"
        assert resolve_tool_name("email_drafter") == "email_draft"
        assert resolve_tool_name("search") == "web_search"

    def test_is_sensitive_tool(self):
        assert is_sensitive_tool("code_exec") is True
        assert is_sensitive_tool("code_executor") is True
        assert is_sensitive_tool("email_draft") is True
        assert is_sensitive_tool("email_drafter") is True
        assert is_sensitive_tool("calc") is False
        assert is_sensitive_tool("file_read") is False
        assert is_sensitive_tool("web_search") is False

    def test_execute_tool_dispatch(self):
        # Calculator dispatch
        calc_res = execute_tool("calc", expression="25 * 4")
        assert calc_res.success is True
        assert calc_res.output == "100"

        # File read dispatch
        file_res = execute_tool("file_read", file_path="dataset.csv", max_lines=2)
        assert file_res.success is True

        # Unknown tool
        unknown_res = execute_tool("nonexistent_tool_abc")
        assert unknown_res.success is False
        assert "Unknown tool" in (unknown_res.error or "")

    def test_langchain_tools_list(self):
        assert len(LANGCHAIN_TOOLS) >= 7
        tool_names = {t.name for t in LANGCHAIN_TOOLS}
        expected = {"calc", "file_read", "code_exec", "web_search", "email_draft", "api_call", "data_analysis", "report_write"}
        assert expected.issubset(tool_names)
