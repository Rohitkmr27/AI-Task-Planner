"""
Safe HTTP API Caller Tool.

Executes API requests (GET/POST) with timeout controls, response parsing,
and fallback simulation for offline/test environments.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from langchain_core.tools import tool

from src.agent.tools.base import ToolResult


def call_api(
    url: str,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    payload: Optional[str] = None,
    timeout_s: int = 5,
) -> ToolResult:
    """
    Perform a safe HTTP API call with timeouts and structured output.

    Parameters
    ----------
    url : str
        Target HTTP/HTTPS URL.
    method : str
        HTTP Method (GET or POST).
    headers : dict, optional
        Custom request headers.
    payload : str, optional
        JSON or raw string payload for POST requests.
    timeout_s : int
        Request timeout in seconds.

    Returns
    -------
    ToolResult
        Standardised tool result with response body, status code, and timing.
    """
    start_time = time.perf_counter()
    tool_name = "api_call"
    method_upper = method.upper()

    clean_url = url.strip()
    if not clean_url or not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error="Invalid URL. Must begin with http:// or https://",
            duration_s=0.0,
            tokens_used=5,
            requires_approval=False,
        )

    req_headers = {"User-Agent": "AITaskPlannerAgent/1.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    data_bytes = None
    if payload and method_upper in ("POST", "PUT", "PATCH"):
        data_bytes = payload.encode("utf-8")
        if "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

    try:
        req = urllib.request.Request(clean_url, data=data_bytes, headers=req_headers, method=method_upper)
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            status_code = response.status
            content = response.read().decode("utf-8", errors="replace")

        # Try to pretty print JSON if possible
        try:
            parsed = json.loads(content)
            formatted = json.dumps(parsed, indent=2)
        except Exception:
            formatted = content

        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=True,
            output=f"Status: {status_code}\nResponse:\n{formatted[:3000]}",
            error=None,
            duration_s=round(duration, 4),
            tokens_used=min(3000, max(50, len(formatted) // 4)),
            requires_approval=False,
            metadata={"status_code": status_code, "url": clean_url},
        )

    except urllib.error.HTTPError as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"HTTP Error {e.code}: {e.reason}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
            metadata={"status_code": e.code},
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"API Request failed: {e}",
            duration_s=round(duration, 4),
            tokens_used=10,
            requires_approval=False,
        )


@tool("api_call")
def api_caller_tool(url: str, method: str = "GET", payload: str = "") -> str:
    """
    Make an HTTP GET or POST request to an external API endpoint.
    Safely captures status code and response payload with timeout limits.
    """
    res = call_api(url=url, method=method, payload=payload if payload else None)
    if res.success:
        return res.output
    return f"Error: {res.error}"
