"""
Interactive Plan Editor Component.

Enables human operators to inspect, customize, reorder, and approve
multi-step agent plans before or during execution.
"""

from __future__ import annotations

import json
from typing import Any
import streamlit as st

from src.agent.tools.registry import get_available_tools, is_sensitive_tool, resolve_tool_name


TOOL_ICONS: dict[str, str] = {
    "calc": "🧮",
    "file_read": "📂",
    "code_exec": "💻",
    "web_search": "🔍",
    "email_draft": "✉️",
    "api_call": "🌐",
    "data_analysis": "📊",
    "report_write": "📝",
}

TOOL_TEMPLATES: dict[str, dict[str, Any]] = {
    "calc": {"expression": "sqrt(144) * 3"},
    "file_read": {"file_path": "dataset.csv", "max_lines": 5},
    "data_analysis": {"file_path": "dataset.csv", "operation": "summary"},
    "web_search": {"query": "LangGraph agent architecture", "num_results": 3},
    "code_exec": {"code": "print('Task executed successfully.')"},
    "email_draft": {"to": "stakeholder@company.com", "subject": "Task Update", "body": "Summary of findings."},
    "api_call": {"url": "https://api.github.com", "method": "GET"},
    "report_write": {"title": "Task Report", "executive_summary": "Summary of execution."},
}


def render_plan_editor(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Render an interactive plan editor allowing operators to review and modify steps.
    """
    if not plan:
        st.info("No plan steps to edit.")
        return plan

    st.markdown("### 🛠️ Interactive Plan Review & Step Customizer")
    st.caption("Review and customize parameters before execution. Add, remove, or modify tool arguments.")

    edited_plan: list[dict[str, Any]] = []

    for i, step in enumerate(plan):
        tool = step.get("tool_called", "calc")
        icon = TOOL_ICONS.get(tool, "⚙️")
        order = i + 1
        is_sensitive = is_sensitive_tool(tool)

        with st.expander(f"{icon} Step {order}: {tool.upper()} — {step.get('description', '')[:50]}", expanded=True):
            col_t, col_s = st.columns([0.7, 0.3])
            with col_t:
                desc = st.text_input(
                    f"Step {order} Description:",
                    value=step.get("description", f"Execute {tool}"),
                    key=f"step_desc_{i}",
                )
            with col_s:
                if is_sensitive:
                    st.warning("⚠️ **Sensitive Tool** (HITL Gate)")
                else:
                    st.info("🛡️ **Safe Tool** (Auto-Executable)")

            # JSON Argument Editor
            raw_input = step.get("tool_input", {})
            input_str = json.dumps(raw_input, indent=2)

            updated_input_str = st.text_area(
                f"Parameters (JSON):",
                value=input_str,
                key=f"step_input_{i}",
                height=110,
            )

            try:
                parsed_input = json.loads(updated_input_str)
            except Exception:
                st.error("Invalid JSON syntax in parameters. Please correct before proceeding.")
                parsed_input = raw_input

            col_del, col_space = st.columns([0.2, 0.8])
            with col_del:
                delete_clicked = st.button(f"🗑️ Delete Step {order}", key=f"del_step_{i}")

            if not delete_clicked:
                edited_plan.append({
                    "step_order": len(edited_plan) + 1,
                    "tool_called": tool,
                    "tool_input": parsed_input,
                    "description": desc,
                    "requires_approval": is_sensitive,
                })

    # Add new step expander
    with st.expander("➕ Add Custom Step to Plan", expanded=False):
        c_tool, c_add = st.columns([0.7, 0.3])
        with c_tool:
            new_tool = st.selectbox(
                "Choose Tool to Add:",
                options=get_available_tools(),
                key="new_step_tool_select",
            )
        default_tpl = TOOL_TEMPLATES.get(new_tool, {})
        new_desc = st.text_input("New Step Description:", value=f"Run {new_tool}", key="new_step_desc")
        new_input_raw = st.text_area("Parameters (JSON):", value=json.dumps(default_tpl, indent=2), key="new_step_json")

        with c_add:
            st.write("")
            st.write("")
            if st.button("Add Step to Plan", type="secondary"):
                try:
                    new_params = json.loads(new_input_raw)
                    edited_plan.append({
                        "step_order": len(edited_plan) + 1,
                        "tool_called": new_tool,
                        "tool_input": new_params,
                        "description": new_desc,
                        "requires_approval": is_sensitive_tool(new_tool),
                    })
                    st.success(f"Added {new_tool} step!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

    return edited_plan
