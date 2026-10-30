"""
Safe File Reading and Inspection Tool.

Permits reading and inspecting allowed file types (.csv, .json, .txt, .md, .py)
strictly within permitted directories. Enforces directory traversal protection
and read-only access.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from langchain_core.tools import tool

from src.agent.tools.base import ToolResult
from src.config.settings import get_settings


ALLOWED_EXTENSIONS = {".csv", ".txt", ".md", ".json", ".py", ".sql", ".log"}


def is_path_allowed(target_path: Path, allowed_dirs: list[Path]) -> bool:
    """
    Check whether a target path resolves inside any of the allowed directories.
    Prevents directory traversal (e.g. ../../).
    """
    try:
        resolved_target = target_path.resolve()
        for allowed in allowed_dirs:
            resolved_allowed = allowed.resolve()
            # Check if resolved_target is allowed directory itself or a subpath
            if resolved_target == resolved_allowed or resolved_allowed in resolved_target.parents:
                return True
        return False
    except Exception:
        return False


def read_file_safe(
    file_path: str,
    max_lines: int = 100,
    allowed_dirs: Optional[list[Path]] = None,
) -> ToolResult:
    """
    Safely read and summarise a file within allowed directories.

    Parameters
    ----------
    file_path : str
        Relative or absolute path to the file.
    max_lines : int
        Maximum lines of text or preview rows to return.
    allowed_dirs : list[Path], optional
        List of directory Paths to restrict access to. Defaults to settings.allowed_dirs_list.

    Returns
    -------
    ToolResult
        Standardised tool result with file contents or error details.
    """
    start_time = time.perf_counter()
    tool_name = "file_read"
    settings = get_settings()

    if allowed_dirs is None:
        allowed_dirs = settings.allowed_dirs_list

    path_obj = Path(file_path)
    if not path_obj.is_absolute():
        path_obj = settings.project_root / file_path

    # Directory traversal safety check
    if not is_path_allowed(path_obj, allowed_dirs):
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Access denied: '{file_path}' is outside permitted directories.",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )

    # Check file exists and is a file
    if not path_obj.exists():
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"File not found: '{file_path}'",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )

    if not path_obj.is_file():
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Target path '{file_path}' is a directory, not a file.",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )

    ext = path_obj.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"File extension '{ext}' is not permitted. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )

    try:
        # CSV handling
        if ext == ".csv":
            try:
                df = pd.read_csv(path_obj)
                shape_info = f"CSV File: {path_obj.name}\nDimensions: {df.shape[0]} rows × {df.shape[1]} columns\n"
                columns_info = f"Columns: {', '.join(df.columns.tolist())}\n\n"
                preview = df.head(min(max_lines, 20)).to_string(index=False)
                output = shape_info + columns_info + "Data Preview (first rows):\n" + preview
                duration = time.perf_counter() - start_time
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    output=output,
                    duration_s=round(duration, 4),
                    tokens_used=min(4000, max(50, len(output) // 4)),
                    requires_approval=False,
                    metadata={"file": str(path_obj), "rows": len(df), "cols": len(df.columns)},
                )
            except Exception:
                # Fall through to raw text line reading if pandas parser encounters irregular formatting
                pass

        # JSON handling
        if ext == ".json":
            with open(path_obj, "r", encoding="utf-8") as f:
                data = json.load(f)
            formatted = json.dumps(data, indent=2)
            lines = formatted.splitlines()
            if len(lines) > max_lines:
                output = "\n".join(lines[:max_lines]) + f"\n... [Truncated: {len(lines) - max_lines} more lines]"
            else:
                output = formatted
            duration = time.perf_counter() - start_time
            return ToolResult(
                tool_name=tool_name,
                success=True,
                output=output,
                duration_s=round(duration, 4),
                tokens_used=min(4000, max(50, len(output) // 4)),
                requires_approval=False,
                metadata={"file": str(path_obj)},
            )

        # Text / Markdown / Code handling
        with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines + 1)]

        is_truncated = len(lines) > max_lines
        content = "".join(lines[:max_lines])
        if is_truncated:
            content += f"\n... [Truncated at {max_lines} lines]"

        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=True,
            output=content,
            duration_s=round(duration, 4),
            tokens_used=min(4000, max(50, len(content) // 4)),
            requires_approval=False,
            metadata={"file": str(path_obj), "truncated": is_truncated},
        )

    except Exception as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Error reading file '{file_path}': {e}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )


@tool("file_read")
def file_reader_tool(file_path: str) -> str:
    """
    Safely read and preview content from an allowed file (.csv, .json, .txt, .md, .py).
    Enforces directory boundaries and prevents unauthorized access.
    """
    res = read_file_safe(file_path)
    if res.success:
        return res.output
    return f"Error: {res.error}"
