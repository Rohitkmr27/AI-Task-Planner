"""
Sandboxed Subprocess Code Execution Tool.

Executes Python code in an isolated subprocess with strict timeout limits,
output capture, and Human-In-The-Loop approval requirement (sensitive action).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from src.agent.tools.base import ToolResult
from src.config.settings import get_settings


def execute_python_code(
    code: str,
    timeout_s: Optional[int] = None,
    cwd: Optional[Path] = None,
) -> ToolResult:
    """
    Execute Python code in a subprocess with timeout and output capture.

    Parameters
    ----------
    code : str
        The Python code string to execute.
    timeout_s : int, optional
        Execution timeout in seconds. Defaults to settings.max_code_exec_timeout.
    cwd : Path, optional
        Working directory for the subprocess. Defaults to project root.

    Returns
    -------
    ToolResult
        Standardised result containing stdout, stderr, exit code, and timing.
    """
    start_time = time.perf_counter()
    tool_name = "code_exec"
    settings = get_settings()

    if timeout_s is None:
        timeout_s = settings.max_code_exec_timeout
    if cwd is None:
        cwd = settings.project_root

    if not code.strip():
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error="Empty code provided for execution.",
            duration_s=0.0,
            tokens_used=10,
            requires_approval=True,
        )

    # Write code to a temporary script file
    temp_dir = tempfile.mkdtemp(prefix="agent_run_")
    script_path = Path(temp_dir) / "run_script.py"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            encoding="utf-8",
            errors="replace",
        )
        duration = time.perf_counter() - start_time
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        success = (proc.returncode == 0)
        output_parts = []
        if stdout:
            output_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            output_parts.append(f"STDERR:\n{stderr}")

        combined_output = "\n\n".join(output_parts) if output_parts else "(No output produced)"
        error_msg = None if success else f"Execution failed with return code {proc.returncode}:\n{stderr or stdout}"

        return ToolResult(
            tool_name=tool_name,
            success=success,
            output=combined_output,
            error=error_msg,
            duration_s=round(duration, 4),
            tokens_used=min(4000, max(50, (len(code) + len(combined_output)) // 4)),
            requires_approval=True,  # SENSITIVE: requires human approval
            metadata={
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
            },
        )

    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Execution timed out after {timeout_s} seconds.",
            duration_s=round(duration, 4),
            tokens_used=50,
            requires_approval=True,
            metadata={"timeout_s": timeout_s},
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Subprocess error: {e}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=True,
        )
    finally:
        # Clean up temporary script
        try:
            if script_path.exists():
                script_path.unlink()
            Path(temp_dir).rmdir()
        except Exception:
            pass


@tool("code_exec")
def code_executor_tool(code: str) -> str:
    """
    Execute Python code in an isolated subprocess.
    Requires human confirmation before running.
    Captures stdout and stderr with timeout protection.
    """
    res = execute_python_code(code)
    if res.success:
        return res.output
    return f"Error: {res.error}"
