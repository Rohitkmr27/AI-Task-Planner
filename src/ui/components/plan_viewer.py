"""
Plan Viewer Component for Streamlit UI.

Renders multi-step execution plans with step badges, tool icons,
sensitive action indicators, and input parameter summaries.
"""

from __future__ import annotations

from typing import Any
import streamlit as st


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


def render_plan(plan: list[dict[str, Any]], current_step_index: int = 0) -> None:
    """
    Render the execution plan as an interactive timeline.
    """
    if not plan:
        st.info("No execution plan generated yet. Enter a task goal above to create one.")
        return

    st.markdown(f"### 📋 Execution Plan ({len(plan)} Steps)")

    for i, step in enumerate(plan):
        tool = step.get("tool_called", "unknown")
        icon = TOOL_ICONS.get(tool, "⚙️")
        order = step.get("step_order", i + 1)
        desc = step.get("description", f"Execute {tool}")
        is_sensitive = step.get("requires_approval", False)

        # Highlight current step vs past vs upcoming
        if i < current_step_index:
            badge = "✅ Completed"
            border_style = "border-left: 4px solid #10b981;"
        elif i == current_step_index:
            badge = "⏳ Current"
            border_style = "border-left: 4px solid #3b82f6;"
        else:
            badge = "⚪ Pending"
            border_style = "border-left: 4px solid #9ca3af;"

        with st.container():
            col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
            with col1:
                st.markdown(f"### {icon}")
            with col2:
                st.markdown(f"**Step {order}:** `{tool}` — {desc}")
                if is_sensitive:
                    st.caption("⚠️ **Sensitive Action:** Requires human confirmation before execution.")
            with col3:
                st.caption(badge)

            with st.expander(f"Parameters for Step {order}", expanded=False):
                st.json(step.get("tool_input", {}))

            st.markdown("---")
