"""
Enterprise Task Planner Page — Interactive Two-Phase Planning, Step Debugger, and Telemetry.
"""

from __future__ import annotations

import json
import uuid
import streamlit as st

from src.agent.executor import execute_step_node
from src.agent.graph import build_agent_graph
from src.agent.planner import create_plan
from src.agent.state import AgentState
from src.agent.summarizer import summarize_node
from src.config.settings import get_settings
from src.db.repository import ExecutionRepository
from src.ui.components.export_tools import render_export_buttons
from src.ui.components.plan_editor import render_plan_editor
from src.ui.components.plan_viewer import render_plan
from src.ui.components.telemetry_viewer import render_telemetry
from src.ui.components.trace_viewer import render_trace
from src.ui.styles import apply_enterprise_theme


st.set_page_config(
    page_title="Task Planner | Agentic AI",
    page_icon="⚡",
    layout="wide",
)

# Apply enterprise dark-mode theme
apply_enterprise_theme()

st.markdown('<div class="enterprise-header">⚡ Agentic Task Planner & Controller</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header-tag">Interactive Two-Phase Planning • Step-Through Debugger • Human-in-the-Loop Gate</div>', unsafe_allow_html=True)

settings = get_settings()
repo = ExecutionRepository()

# Sidebar: Enterprise Controls
with st.sidebar:
    st.markdown("### 🎛️ Operator Control Panel")
    exec_mode = st.radio(
        "Execution Strategy",
        ["Continuous Run", "Step-by-Step (Debugger)"],
        help="Continuous runs entire plan autonomously; Step-by-Step pauses after each tool execution.",
    )
    auto_approve = st.checkbox(
        "Auto-Authorize Sensitive Tools",
        value=False,
        help="If unchecked, sensitive tools (code_exec, email_draft) will pause for your confirmation.",
    )
    max_retries = st.slider("Max Retries Per Step", min_value=0, max_value=3, value=2)
    selected_model = st.selectbox(
        "Gemini Model",
        options=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        index=0,
    )
    st.markdown("---")
    st.markdown("**🛡️ Active Safety Policies:**")
    st.caption("• AST-Isolated Calculator (No eval)")
    st.caption("• Path-Restricted File Reader")
    st.caption("• Subprocess Timeout (10s)")
    st.caption("• Draft-Only Watermarked Emails")

# Initialize Session State
if "run_id" not in st.session_state or not st.session_state["run_id"]:
    st.session_state["run_id"] = f"run_{uuid.uuid4().hex[:8]}"
if "agent_state" not in st.session_state:
    st.session_state["agent_state"] = None
if "plan_generated" not in st.session_state:
    st.session_state["plan_generated"] = False

# Quick Preset Buttons
st.markdown("**Enterprise Task Presets:**")
c_p1, c_p2, c_p3, c_p4 = st.columns(4)
with c_p1:
    if st.button("📊 Exploratory Data Analysis"):
        st.session_state["task_input"] = "Inspect dataset.csv, perform a statistical summary of columns, and draft a short report"
with c_p2:
    if st.button("🧮 Safe Math & Statistics"):
        st.session_state["task_input"] = "Calculate sqrt(1024) * (45 / 3) + factorial(5)"
with c_p3:
    if st.button("🔍 Autonomous Web Research"):
        st.session_state["task_input"] = "Research state-of-the-art agentic AI task decomposition and self-reflection patterns"
with c_p4:
    if st.button("✉️ Project Milestone Update"):
        st.session_state["task_input"] = "Draft a formal project update email to supervisor@company.com summarizing completed milestones"

default_val = st.session_state.get("task_input", "")
user_goal = st.text_area(
    "Task Objective (Natural Language):",
    value=default_val,
    height=90,
    placeholder="E.g., Analyze dataset.csv, calculate the mean duration of tool calls, and draft an executive report...",
)

# Phase 1: Planning Trigger
c_btn1, c_btn2, c_space = st.columns([0.22, 0.22, 0.56])
with c_btn1:
    plan_clicked = st.button("🧠 1. Generate Plan", type="primary", use_container_width=True)
with c_btn2:
    reset_clicked = st.button("🔄 Reset / Clear Session", use_container_width=True)

if reset_clicked:
    st.session_state["run_id"] = f"run_{uuid.uuid4().hex[:8]}"
    st.session_state["agent_state"] = None
    st.session_state["plan_generated"] = False
    st.session_state["task_input"] = ""
    st.rerun()

if plan_clicked and user_goal.strip():
    run_id = st.session_state["run_id"]
    repo.create_run(user_goal=user_goal.strip(), run_id=run_id)

    with st.spinner("Decomposing objective into structured tool steps..."):
        generated_plan = create_plan(user_goal.strip())

    initial_state: AgentState = {
        "run_id": run_id,
        "user_goal": user_goal.strip(),
        "plan": generated_plan,
        "current_step_index": 0,
        "step_results": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "status": "pending",
        "final_result": None,
        "error_message": None,
        "total_tokens": 0,
        "total_duration": 0.0,
        "auto_approve": auto_approve,
        "human_approved": True if auto_approve else None,
    }
    st.session_state["agent_state"] = initial_state
    st.session_state["plan_generated"] = True
    repo.update_run_plan(run_id, generated_plan)
    st.rerun()

current_state = st.session_state.get("agent_state")

if current_state and st.session_state.get("plan_generated"):
    plan = current_state.get("plan", [])
    step_idx = current_state.get("current_step_index", 0)
    status = current_state.get("status", "pending")
    step_results = current_state.get("step_results", [])
    run_id = current_state.get("run_id")

    st.markdown("---")

    # If execution hasn't started yet, allow editing the plan
    if status == "pending" and step_idx == 0 and not step_results:
        customized_plan = render_plan_editor(plan)
        current_state["plan"] = customized_plan
        current_state["auto_approve"] = auto_approve

        st.markdown("---")
        c_exec_cont, c_exec_step, c_emp = st.columns([0.25, 0.25, 0.5])
        with c_exec_cont:
            run_continuous = st.button("🚀 2. Execute Plan (Continuous)", type="primary", use_container_width=True)
        with c_exec_step:
            run_step_by_step = st.button("⏭️ 2. Step-by-Step (Debugger)", use_container_width=True)

        if run_continuous:
            current_state["status"] = "running"
            repo.update_run_status(run_id, "running")
            graph = build_agent_graph(repo=repo)
            config = {"configurable": {"thread_id": run_id}}
            with st.spinner("Executing agent plan..."):
                final_out = graph.invoke(current_state, config=config)
                st.session_state["agent_state"] = final_out
                st.rerun()

        if run_step_by_step:
            current_state["status"] = "running"
            repo.update_run_status(run_id, "running")
            with st.spinner("Executing Step 1..."):
                update = execute_step_node(current_state, repo=repo)
                current_state.update(update)
                if current_state.get("current_step_index", 0) >= len(current_state.get("plan", [])) or current_state.get("status") == "completed":
                    current_state["status"] = "completed"
                    sum_res = summarize_node(current_state, repo=repo)
                    current_state.update(sum_res)
                st.session_state["agent_state"] = current_state
                st.rerun()

    else:
        # Execution is in progress or completed
        render_plan(plan, current_step_index=step_idx)

        # Human-in-the-Loop Gate Modal
        if status == "awaiting_approval" and step_idx < len(plan):
            sensitive_step = plan[step_idx]
            tool_name = sensitive_step.get("tool_called")

            st.warning(f"⚠️ **Human-in-the-Loop Confirmation Required for Step {step_idx + 1}: `{tool_name}`**")
            st.markdown(f"**Action Description:** {sensitive_step.get('description')}")
            st.json(sensitive_step.get("tool_input", {}))

            c_app, c_rej = st.columns([0.2, 0.2])
            with c_app:
                if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
                    current_state["human_approved"] = True
                    current_state["status"] = "running"
                    if exec_mode == "Step-by-Step (Debugger)":
                        with st.spinner(f"Executing Step {step_idx + 1}..."):
                            update = execute_step_node(current_state, repo=repo)
                            current_state.update(update)
                    else:
                        graph = build_agent_graph(repo=repo)
                        config = {"configurable": {"thread_id": run_id}}
                        with st.spinner("Resuming execution with approval..."):
                            current_state = graph.invoke(current_state, config=config)
                    st.session_state["agent_state"] = current_state
                    st.rerun()

            with c_rej:
                if st.button("❌ Reject Action", use_container_width=True):
                    current_state["status"] = "cancelled"
                    current_state["error_message"] = "Execution cancelled by human operator."
                    repo.update_run_status(run_id, "cancelled", error_message="Rejected by operator")
                    st.session_state["agent_state"] = current_state
                    st.rerun()

        # Step-by-Step Next Step Trigger
        elif status == "running" and step_idx < len(plan):
            st.info(f"📍 Paused in Debugger Mode before Step {step_idx + 1} of {len(plan)}.")
            c_next, c_cont_all = st.columns([0.25, 0.25])
            with c_next:
                if st.button(f"⏭️ Execute Step {step_idx + 1}: `{plan[step_idx]['tool_called']}`", type="primary", use_container_width=True):
                    with st.spinner(f"Executing step {step_idx + 1}..."):
                        update = execute_step_node(current_state, repo=repo)
                        current_state.update(update)
                        # If reached the end, summarize
                        if current_state.get("current_step_index", 0) >= len(plan):
                            current_state["status"] = "completed"
                            sum_res = summarize_node(current_state, repo=repo)
                            current_state.update(sum_res)
                        st.session_state["agent_state"] = current_state
                        st.rerun()
            with c_cont_all:
                if st.button("🚀 Run Remaining Steps Continuously", use_container_width=True):
                    graph = build_agent_graph(repo=repo)
                    config = {"configurable": {"thread_id": run_id}}
                    with st.spinner("Finishing remaining steps..."):
                        final_out = graph.invoke(current_state, config=config)
                        st.session_state["agent_state"] = final_out
                        st.rerun()

        # Live Telemetry
        if step_results:
            st.markdown("---")
            render_telemetry(
                step_results=step_results,
                total_tokens=current_state.get("total_tokens", 0),
                total_duration=current_state.get("total_duration", 0.0),
            )

            st.markdown("---")
            render_trace(step_results)

        # Final Synthesized Result & Exporter
        if current_state.get("final_result"):
            st.markdown("---")
            st.success("### 🏁 Final Execution Result & Synthesis")
            st.markdown(current_state["final_result"])

            st.markdown("---")
            render_export_buttons(
                run_id=run_id,
                user_goal=user_goal,
                plan=plan,
                step_results=step_results,
                final_result=current_state.get("final_result"),
                total_tokens=current_state.get("total_tokens", 0),
                total_duration=current_state.get("total_duration", 0.0),
            )
