"""
Task Planning Module for the Agentic AI Task Planner.

Decomposes a user's natural language goal into a sequence of executable tool steps.
Supports Google Gemini via langchain-google-genai, with automatic fallback
to an intelligent rule-based planner for offline or credit-free testing.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.agent.state import AgentState, PlanStep
from src.agent.tools.registry import get_available_tools, is_sensitive_tool, resolve_tool_name
from src.config.settings import get_settings


PLANNER_SYSTEM_PROMPT = """You are an expert AI Task Planner.
Your job is to decompose the user's natural language goal into a sequence of executable steps using available tools.

AVAILABLE TOOLS:
- calc: Evaluate mathematical expressions (e.g. {"expression": "sqrt(144) + 10"})
- file_read: Read and preview files (.csv, .json, .txt, .md, .py) (e.g. {"file_path": "dataset.csv", "max_lines": 10})
- data_analysis: Perform pandas statistical analysis (e.g. {"file_path": "dataset.csv", "operation": "summary"})
- web_search: Research documentation and topics (e.g. {"query": "agentic AI task planner"})
- code_exec: Execute Python code in a subprocess [SENSITIVE - REQUIRES APPROVAL] (e.g. {"code": "print('hello')"})
- email_draft: Draft professional email communication [SENSITIVE - REQUIRES APPROVAL] (e.g. {"to": "team@example.com", "subject": "Update", "body": "Report completed."})
- api_call: Query external HTTP API (e.g. {"url": "https://api.github.com"})
- report_write: Format structured markdown report (e.g. {"title": "Summary", "executive_summary": "Done.", "key_findings": ["F1", "F2"]})

RULES:
1. Return ONLY a valid JSON array of step objects. No markdown formatting, no commentary.
2. Each step must have:
   - "step_order": integer (1, 2, 3...)
   - "tool_called": string (exact tool name from above)
   - "tool_input": object (key-value parameters for the tool)
   - "description": string (short description of the step)
3. Keep the plan concise and goal-focused (maximum 6 steps).
"""


def _heuristic_planner(user_goal: str) -> list[PlanStep]:
    """
    Intelligent heuristic fallback planner when Gemini API is unavailable.
    Decomposes common agent tasks based on intent analysis.
    """
    g_lower = user_goal.lower()
    steps: list[PlanStep] = []
    order = 1

    # Data analysis or dataset inspection
    if any(k in g_lower for k in ["dataset", "csv", "data analysis", "summary", "stats", "distribution", "eda"]):
        steps.append({
            "step_order": order,
            "tool_called": "file_read",
            "tool_input": {"file_path": "dataset.csv", "max_lines": 5},
            "description": "Inspect dataset schema and first rows",
            "requires_approval": False,
        })
        order += 1
        steps.append({
            "step_order": order,
            "tool_called": "data_analysis",
            "tool_input": {"file_path": "dataset.csv", "operation": "summary"},
            "description": "Compute descriptive statistics on dataset",
            "requires_approval": False,
        })
        order += 1

    # Web research
    if any(k in g_lower for k in ["search", "research", "find", "explore", "learn", "architecture", "overview"]):
        query = re.sub(r"^(search for|research|find|look up)\s*", "", user_goal, flags=re.I).strip()
        steps.append({
            "step_order": order,
            "tool_called": "web_search",
            "tool_input": {"query": query or user_goal, "num_results": 3},
            "description": f"Search the web for information on '{query or user_goal}'",
            "requires_approval": False,
        })
        order += 1

    # Calculation
    if any(k in g_lower for k in ["calculate", "calc", "math", "evaluate", "compute", "+", "*", "sqrt", "%"]):
        clean_goal = re.sub(
            r"^(calculate|calc|compute|evaluate|what is|find the value of)\s*",
            "",
            user_goal,
            flags=re.I,
        ).strip().rstrip(".?!;:")
        expr = clean_goal if clean_goal else "2 + 2"
        steps.append({
            "step_order": order,
            "tool_called": "calc",
            "tool_input": {"expression": expr},
            "description": f"Calculate mathematical expression: {expr}",
            "requires_approval": False,
        })
        order += 1

    # Python Code execution
    if any(k in g_lower for k in ["code", "python", "script", "execute code", "run code"]):
        steps.append({
            "step_order": order,
            "tool_called": "code_exec",
            "tool_input": {"code": "print('Task executed successfully.')"},
            "description": "Execute Python code script",
            "requires_approval": True,
        })
        order += 1

    # Email draft
    if any(k in g_lower for k in ["email", "draft", "notify", "send update", "mail"]):
        steps.append({
            "step_order": order,
            "tool_called": "email_draft",
            "tool_input": {
                "to": "supervisor@example.com",
                "subject": f"Update regarding: {user_goal[:40]}",
                "body": f"Automated summary for requested task: {user_goal}",
            },
            "description": "Draft summary email for stakeholders",
            "requires_approval": True,
        })
        order += 1

    # Report write
    if any(k in g_lower for k in ["report", "writeup", "document", "findings", "summary"]):
        steps.append({
            "step_order": order,
            "tool_called": "report_write",
            "tool_input": {
                "title": f"Report: {user_goal[:50]}",
                "executive_summary": f"Findings for user task: {user_goal}",
                "key_findings": ["Analyzed task requirements.", "Completed execution steps."],
            },
            "description": "Generate final markdown report",
            "requires_approval": False,
        })
        order += 1

    # Fallback default if no keywords matched
    if not steps:
        steps.append({
            "step_order": 1,
            "tool_called": "web_search",
            "tool_input": {"query": user_goal, "num_results": 3},
            "description": f"Research information on: {user_goal}",
            "requires_approval": False,
        })
        steps.append({
            "step_order": 2,
            "tool_called": "report_write",
            "tool_input": {
                "title": f"Task Summary: {user_goal}",
                "executive_summary": f"Execution summary for: {user_goal}",
                "key_findings": [f"Processed task: {user_goal}"],
            },
            "description": "Draft summary report",
            "requires_approval": False,
        })

    return steps


def create_plan(user_goal: str) -> list[PlanStep]:
    """
    Generate an execution plan for a user goal.
    Uses Gemini LLM if configured; otherwise falls back to heuristic planner.
    """
    settings = get_settings()

    if settings.has_google_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                temperature=settings.gemini_temperature,
                google_api_key=settings.google_api_key.get_secret_value(),
            )
            response = llm.invoke([
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Decompose this task into steps:\n{user_goal}"},
            ])
            content = response.content.strip()

            # Clean JSON if wrapped in markdown code blocks
            if "```" in content:
                content = re.sub(r"^```(?:json)?", "", content.strip(), flags=re.MULTILINE)
                content = content.rstrip("`").strip()

            raw_steps = json.loads(content)
            if isinstance(raw_steps, list) and len(raw_steps) > 0:
                validated_steps: list[PlanStep] = []
                for i, s in enumerate(raw_steps, 1):
                    tool_raw = s.get("tool_called", "")
                    tool_canonical = resolve_tool_name(tool_raw)
                    validated_steps.append({
                        "step_order": i,
                        "tool_called": tool_canonical,
                        "tool_input": s.get("tool_input", {}),
                        "description": s.get("description", f"Execute {tool_canonical}"),
                        "requires_approval": is_sensitive_tool(tool_canonical),
                    })
                return validated_steps[:settings.max_steps_per_run]
        except Exception:
            # Fall back smoothly to heuristic planner on API errors
            pass

    return _heuristic_planner(user_goal)[:settings.max_steps_per_run]


def plan_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: generates execution plan from user_goal.
    """
    user_goal = state.get("user_goal", "")
    plan = create_plan(user_goal)
    return {
        "plan": plan,
        "current_step_index": 0,
        "status": "running" if plan else "failed",
        "error_message": None if plan else "Planner failed to generate steps.",
    }
