"""
Main Streamlit Application Entry Point.
Agentic AI Task Planner — HCLTech Career Shaper Programme.
"""

from __future__ import annotations

import streamlit as st

from src.agent.tools.registry import get_available_tools
from src.config.settings import get_settings
from src.db.repository import ExecutionRepository
from src.ui.styles import apply_enterprise_theme


# Streamlit page configuration
st.set_page_config(
    page_title="Agentic AI Task Planner",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply enterprise design tokens
apply_enterprise_theme()


def main():
    get_settings.cache_clear()
    settings = get_settings()
    repo = ExecutionRepository()

    st.markdown('<div class="enterprise-header">🤖 Agentic AI Task Planner</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header-tag">Autonomous Multi-Step AI Agent Architecture • LangGraph Engine • Sandboxed Tool Use</div>', unsafe_allow_html=True)
    st.caption(f"Connected to SQLite runtime DB: `{settings.database_path}` | Gemini Model: `{settings.gemini_model}`")

    st.markdown("---")

    # High-level metrics row
    total_runs = repo.count_runs()
    completed_runs = repo.count_runs(status="completed")
    available_tools = get_available_tools()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Total Task Runs</div>
                <div class="metric-value">{total_runs}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Completed Tasks</div>
                <div class="metric-value">{completed_runs}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Registered Tools</div>
                <div class="metric-value">{len(available_tools)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        has_key = "Active ✅" if settings.has_google_api_key else "Offline / Heuristic ⚠️"
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Gemini API Status</div>
                <div class="metric-value" style="font-size: 1.3rem;">{has_key}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Architecture & Key Features
    col_left, col_right = st.columns([0.58, 0.42])

    with col_left:
        st.subheader("System Architecture & Design")
        st.markdown(
            """
            This application implements an autonomous multi-step agent orchestrator using **LangGraph**:
            - **Two-Phase Interactive Workflow:** Decomposes natural language requests into structured steps and provides an operator review room to customize tool arguments before execution.
            - **Sandboxed Tool Registry:** Features 8 sandboxed tools (Math via AST, File Reader with path boundaries, Pandas Analyzer, Web Researcher, Subprocess Code Executor, Watermarked Email Drafter, HTTP API Caller, and Report Writer).
            - **Human-in-the-Loop (HITL) Gate:** Pauses execution and requires explicit human confirmation before executing sensitive tools (`code_exec`, `email_draft`).
            - **Error Recovery & Retries:** Handles tool exceptions with configurable retry budgets and fallback options.
            - **Full Observability & Telemetry:** Logs full execution traces, latency waterfalls, token consumption, and audit trails to SQLite.
            """
        )

        st.info("👈 Use the **Sidebar Navigation** to launch the **1_Task_Planner**, inspect **2_Execution_Logs**, or explore the **3_EDA_Dashboard**.")

    with col_right:
        st.subheader("Supported Task Categories")
        categories = [
            ("📊 Data Analysis", "Read CSV files, compute summary statistics, distributions, groupings."),
            ("📝 Report Writing", "Synthesize findings into clean Markdown technical reports."),
            ("🔍 Web Research", "Query documentation, search engines, or curated research caches."),
            ("🧮 Mathematical Calculations", "Evaluate arithmetic, powers, and trigonometric functions with AST safety."),
            ("💻 Python Code Execution", "Run Python scripts in a subprocess with timeouts & safety approvals."),
            ("📂 Safe File Reading", "Inspect CSV, JSON, TXT within allowed directories."),
            ("✉️ Email Drafting", "Draft stakeholder messages with watermark — never auto-sends."),
        ]
        for name, desc in categories:
            st.markdown(f"**{name}** — <span style='color: #94a3b8; font-size: 0.88rem;'>{desc}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Recent Execution Activity")
    recent = repo.get_recent_activity(limit=5)
    if recent:
        st.dataframe(recent, use_container_width=True)
    else:
        st.write("No execution runs logged yet. Go to **1_Task_Planner** to run your first task!")


if __name__ == "__main__":
    main()
