"""
Execution Logs Page — Observability, Runtime Trace Database, and Tool Analytics.
"""

from __future__ import annotations

import json
import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.repository import ExecutionRepository
from src.ui.components.export_tools import render_export_buttons
from src.ui.styles import apply_enterprise_theme


st.set_page_config(page_title="Execution Logs | Agentic AI", page_icon="📜", layout="wide")

# Apply enterprise styling
apply_enterprise_theme()

st.markdown('<div class="enterprise-header">📜 Execution Trace Logs & Observability</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header-tag">Inspect runtime task execution traces, tool invocations, token consumption, and failure logs stored in SQLite.</div>', unsafe_allow_html=True)

repo = ExecutionRepository()

# Filters
col_f1, col_f2 = st.columns([0.3, 0.7])
with col_f1:
    status_filter = st.selectbox("Filter by Status", ["All", "completed", "failed", "running", "awaiting_approval"])
with col_f2:
    search_query = st.text_input("Search User Goal / Keywords", placeholder="Type keywords...")

filter_arg = None if status_filter == "All" else status_filter
runs = repo.list_runs(status=filter_arg, limit=100)

if search_query.strip():
    runs = [r for r in runs if search_query.lower() in r.user_goal.lower()]

runs_data = [r.to_dict() for r in runs]

if not runs_data:
    st.info("No execution runs match your filter criteria.")
else:
    runs_df = pd.DataFrame(runs_data)
    display_cols = [
        "run_id", "user_goal", "status", "created_at",
        "total_steps", "successful_steps", "failed_steps",
        "total_tokens", "total_duration",
    ]
    st.dataframe(runs_df[display_cols], use_container_width=True, height=250)

    # Detailed Drilldown
    st.markdown("---")
    st.subheader("🔍 Run Drill-down")

    run_ids = [r.run_id for r in runs]
    selected_run_id = st.selectbox("Select a Run ID to inspect details:", run_ids)

    if selected_run_id:
        selected_run = repo.get_run(selected_run_id)
        steps = repo.get_steps(selected_run_id)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Goal", selected_run.user_goal[:40] + "...")
        with c2:
            st.metric("Status", selected_run.status.upper())
        with c3:
            st.metric("Total Tokens", selected_run.total_tokens)
        with c4:
            st.metric("Total Duration", f"{selected_run.total_duration:.2f}s")

        if selected_run.final_result:
            with st.expander("Final Result Output", expanded=True):
                st.markdown(selected_run.final_result)

        if steps:
            st.markdown(f"#### Steps Breakdown ({len(steps)} steps)")
            step_dicts = [s.to_dict() for s in steps]
            step_df = pd.DataFrame(step_dicts)
            st.dataframe(
                step_df[["step_order", "tool_called", "tool_success", "tokens_used", "duration_s", "retry_count"]],
                use_container_width=True,
            )

            # Expandable details for each step
            for s in steps:
                flag = "✅" if s.tool_success == 1 else "❌"
                with st.expander(f"{flag} Step {s.step_order}: {s.tool_called}"):
                    c_in, c_out = st.columns(2)
                    with c_in:
                        st.markdown("**Tool Input:**")
                        st.code(s.tool_input or "(None)", language="json")
                    with c_out:
                        st.markdown("**Tool Output:**")
                        st.code(s.tool_output or s.error_message or "(None)", language="text")

            # One-click Export for this historical run
            plan_obj = json.loads(selected_run.plan_json) if selected_run.plan_json else []
            render_export_buttons(
                run_id=selected_run.run_id,
                user_goal=selected_run.user_goal,
                plan=plan_obj,
                step_results=step_dicts,
                final_result=selected_run.final_result,
                total_tokens=selected_run.total_tokens,
                total_duration=selected_run.total_duration,
            )

# Tool Usage Analytics across all runs
st.markdown("---")
st.subheader("📊 Aggregate Tool Usage Analytics (Live DB)")

tool_stats = repo.get_tool_usage_stats()
if tool_stats:
    tool_df = pd.DataFrame(tool_stats)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_invocations = px.bar(
            tool_df,
            x="tool_called",
            y="total_invocations",
            title="Total Invocations by Tool",
            color="tool_called",
            text_auto=True,
            template="plotly_dark",
        )
        st.plotly_chart(fig_invocations, use_container_width=True)

    with col_g2:
        fig_duration = px.bar(
            tool_df,
            x="tool_called",
            y="avg_duration",
            title="Average Latency per Tool (seconds)",
            color="tool_called",
            text_auto=True,
            template="plotly_dark",
        )
        st.plotly_chart(fig_duration, use_container_width=True)
else:
    st.write("No tool steps executed yet to compute aggregate metrics.")
