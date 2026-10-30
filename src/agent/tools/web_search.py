"""
Web Research and Search Tool.

Supports online search via SerpAPI if configured, with graceful fallback
to structured mock search results when offline or without an API key.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional
import urllib.parse
import urllib.request

from langchain_core.tools import tool

from src.agent.tools.base import ToolResult
from src.config.settings import get_settings


def _mock_search(query: str) -> list[dict[str, str]]:
    """Generate realistic structured search results for common AI/task topics."""
    q_lower = query.lower()

    if any(k in q_lower for k in ["langgraph", "agent", "planning", "task planner"]):
        return [
            {
                "title": "LangGraph: Multi-Agent Workflows and State Machines",
                "snippet": "LangGraph enables cyclical graphs for agent orchestration, human-in-the-loop validation, and persistent execution traces.",
                "link": "https://langchain-ai.github.io/langgraph/",
            },
            {
                "title": "Agentic AI Architecture: Task Decomposition and Tool Use",
                "snippet": "Key patterns in autonomous agents: ReAct prompting, plan-and-solve workflows, self-reflection, and error recovery strategies.",
                "link": "https://arxiv.org/abs/2303.11366",
            },
            {
                "title": "Tool Calling and Execution Safety in LLMs",
                "snippet": "Best practices for agentic security include read-only file sandboxing, ast-based calculators, and human confirmation gates for writes.",
                "link": "https://python.langchain.com/docs/concepts/tools/",
            },
        ]
    elif any(k in q_lower for k in ["eda", "dataset", "data analysis", "pandas"]):
        return [
            {
                "title": "Exploratory Data Analysis Best Practices in Python",
                "snippet": "Guidelines for cleaning synthetic traces, computing descriptive statistics, detecting anomalies, and correlation matrices.",
                "link": "https://pandas.pydata.org/docs/user_guide/index.html",
            },
            {
                "title": "Visualizing Execution Metrics: Tokens and Latency",
                "snippet": "Using Plotly and Matplotlib to analyze agent performance distribution, tool failure rates, and retry counts.",
                "link": "https://plotly.com/python/",
            },
        ]
    elif any(k in q_lower for k in ["gemini", "google", "llm"]):
        return [
            {
                "title": "Google Gemini 1.5 Flash and Pro API Documentation",
                "snippet": "Gemini models offer large context windows, function calling capabilities, and fast structured outputs via Google AI Studio.",
                "link": "https://ai.google.dev/gemini-api/docs",
            },
        ]
    else:
        return [
            {
                "title": f"Search Results for: {query}",
                "snippet": f"Overview of relevant literature, reference implementations, and best practices regarding '{query}'.",
                "link": f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}",
            },
            {
                "title": f"Technical Documentation: {query}",
                "snippet": f"Official documentation, tutorials, and standard specifications relating to '{query}'.",
                "link": f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote_plus(query)}",
            },
        ]


def search_web(query: str, num_results: int = 4) -> ToolResult:
    """
    Search the web using SerpAPI or a mock fallback.

    Parameters
    ----------
    query : str
        The search query.
    num_results : int
        Number of search results to return.

    Returns
    -------
    ToolResult
        Structured search results with titles, snippets, and links.
    """
    start_time = time.perf_counter()
    tool_name = "web_search"
    settings = get_settings()

    clean_query = query.strip()
    if not clean_query:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error="Search query cannot be empty.",
            duration_s=0.0,
            tokens_used=5,
            requires_approval=False,
        )

    # Online search via SerpAPI if key available
    if settings.has_serpapi_key:
        try:
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote_plus(clean_query)}&api_key={settings.serpapi_api_key}&num={num_results}"
            req = urllib.request.Request(url, headers={"User-Agent": "AITaskPlannerAgent/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            organic = data.get("organic_results", [])
            results = []
            for item in organic[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                })
            source = "SerpAPI (Live)"
        except Exception:
            # Fallback to mock on network/API failure
            results = _mock_search(clean_query)[:num_results]
            source = "Mock Search (Offline Fallback)"
    else:
        results = _mock_search(clean_query)[:num_results]
        source = "Mock Search (Offline Mode)"

    duration = time.perf_counter() - start_time

    # Format output text
    lines = [f"Search Results for '{clean_query}' [{source}]:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['snippet']}")
        lines.append(f"   URL: {r['link']}\n")

    output_text = "\n".join(lines).strip()

    return ToolResult(
        tool_name=tool_name,
        success=True,
        output=output_text,
        error=None,
        duration_s=round(duration, 4),
        tokens_used=min(3000, max(50, len(output_text) // 4)),
        requires_approval=False,
        metadata={"query": clean_query, "source": source, "results_count": len(results)},
    )


@tool("web_search")
def web_search_tool(query: str) -> str:
    """
    Search the web for information, research, and documentation.
    Works online with SerpAPI or offline via simulated research database.
    """
    res = search_web(query)
    if res.success:
        return res.output
    return f"Error: {res.error}"
