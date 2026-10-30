"""
Execution Trace Viewer Component for Streamlit UI.

Renders detailed step-by-step outcomes, execution timings, token metrics,
and tool inputs/outputs.
"""

from __future__ import annotations

from typing import Any
import streamlit as st


def render_trace(step_results: list[dict[str, Any]]) -> None:
    """
    Render historical or live execution step results.
    """
    if not step_results:
        st.write("No execution steps recorded yet.")
        return

    st.markdown(f"### ⏱️ Execution Trace ({len(step_results)} Steps Recorded)")

    for step in step_results:
        success = step.get("tool_success", 0) == 1
        order = step.get("step_order", "?")
        tool = step.get("tool_called", "unknown")
        duration = step.get("duration_s", 0.0)
        tokens = step.get("tokens_used", 0)
        retries = step.get("retry_count", 0)

        flag_icon = "🟢" if success else "🔴"
        status_text = "Success" if success else "Failed"

        header = f"{flag_icon} Step {order}: {tool} ({status_text} | {duration:.2f}s | {tokens} tokens"
        if retries > 0:
            header += f" | {retries} retries"
        header += ")"

        with st.expander(header, expanded=not success):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Tool Input:**")
                st.code(str(step.get("tool_input", "")), language="json")
            with col2:
                st.markdown("**Tool Output:**")
                out_text = step.get("tool_output", "") or step.get("error_message", "No output")
                st.code(out_text, language="text")

            if step.get("requires_approval"):
                st.caption(f"Human Approval: {'Approved ✅' if step.get('approved') else 'Pending / Auto-approved'}")
