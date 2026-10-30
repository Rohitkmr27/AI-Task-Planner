"""
Exploratory Data Analysis Dashboard for the historical dataset.csv.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from src.eda.analysis import (
    compute_summary_statistics,
    load_dataset,
    run_full_eda,
)
from src.ui.styles import apply_enterprise_theme


st.set_page_config(page_title="EDA Dashboard | Agentic AI", page_icon="📈", layout="wide")

# Apply enterprise styling
apply_enterprise_theme()

st.markdown('<div class="enterprise-header">📈 Exploratory Data Analysis Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header-tag">Comprehensive statistical breakdown, correlation heatmaps, and tool reliability distributions.</div>', unsafe_allow_html=True)

# Load data
df = load_dataset()
stats = compute_summary_statistics(df)

# Top KPI metrics
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Total Executions</div>
            <div class="metric-value">{stats['total_rows']:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Unique Tasks</div>
            <div class="metric-value">{stats['unique_tasks']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Overall Success</div>
            <div class="metric-value">{stats['overall_success_rate']:.1%}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Mean Tokens / Step</div>
            <div class="metric-value">{stats['tokens_used']['mean']:,.0f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c5:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Mean Latency</div>
            <div class="metric-value">{stats['duration_s']['mean']:.1f}s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# Visualisations Section
st.subheader("📊 Visual Analytics")

eda_results = run_full_eda(df, save_to_disk=False)
plotly_figs = eda_results["figures_plotly"]
mpl_figs = eda_results["figures_matplotlib"]

row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    st.plotly_chart(plotly_figs["tool_usage_distribution"], use_container_width=True)
with row1_col2:
    st.plotly_chart(plotly_figs["success_rate_by_tool"], use_container_width=True)

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.plotly_chart(plotly_figs["token_distribution"], use_container_width=True)
with row2_col2:
    st.plotly_chart(plotly_figs["duration_by_tool"], use_container_width=True)

row3_col1, row3_col2 = st.columns(2)
with row3_col1:
    st.plotly_chart(plotly_figs["retry_analysis"], use_container_width=True)
with row3_col2:
    st.plotly_chart(plotly_figs["steps_per_task"], use_container_width=True)

st.markdown("#### Correlation Matrix")
st.pyplot(mpl_figs["correlation_heatmap"])

st.markdown("---")

# Filterable Data Explorer
st.subheader("🔍 Interactive Dataset Explorer")
col_tool, col_succ, col_ret = st.columns(3)
with col_tool:
    selected_tools = st.multiselect(
        "Filter by Tool:",
        options=sorted(df["tool_called"].unique()),
        default=sorted(df["tool_called"].unique()),
    )
with col_succ:
    selected_success = st.multiselect(
        "Filter by Success:",
        options=[1, 0],
        format_func=lambda x: "Success (1)" if x == 1 else "Failure (0)",
        default=[1, 0],
    )
with col_ret:
    selected_retries = st.multiselect(
        "Filter by Retry Count:",
        options=[0, 1, 2],
        default=[0, 1, 2],
    )

filtered_df = df[
    df["tool_called"].isin(selected_tools)
    & df["tool_success"].isin(selected_success)
    & df["retry_count"].isin(selected_retries)
]

st.markdown(f"**Showing {len(filtered_df)} matching rows:**")
st.dataframe(filtered_df, use_container_width=True, height=300)

st.markdown("---")

# Data Dictionary
st.subheader("📖 Data Dictionary Metadata")
dict_path = Path(__file__).resolve().parent.parent.parent.parent / "data_dictionary.csv"
if dict_path.exists():
    data_dict = pd.read_csv(dict_path)
    st.dataframe(data_dict, use_container_width=True)
else:
    st.write("data_dictionary.csv not found.")
