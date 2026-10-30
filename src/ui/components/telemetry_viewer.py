"""
Live Telemetry and Execution Observability Component.

Renders real-time latency waterfall charts, token consumption gauges,
and cost estimation for enterprise visibility.
"""

from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config.settings import get_settings


def render_telemetry(step_results: list[dict[str, Any]], total_tokens: int, total_duration: float) -> None:
    """
    Render live telemetry charts: latency waterfall, token usage, and status breakdown.
    """
    if not step_results:
        return

    settings = get_settings()
    st.markdown("### 📊 Live Execution Telemetry & Performance")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Steps", len(step_results))
    with c2:
        st.metric("Cumulative Duration", f"{total_duration:.2f}s")
    with c3:
        st.metric("Total Tokens Used", f"{total_tokens:,}")
    with c4:
        # Gemini 1.5 Flash approx cost ($0.075 per 1M tokens)
        est_cost = (total_tokens / 1_000_000) * 0.075
        st.metric("Est. Inference Cost", f"${est_cost:.5f}")

    # Latency Waterfall & Token Consumption Charts
    steps_df = pd.DataFrame([
        {
            "Step": f"Step {s.get('step_order', i+1)}: {s.get('tool_called', '')}",
            "Tool": s.get("tool_called", ""),
            "Duration (s)": s.get("duration_s", 0.0),
            "Tokens": s.get("tokens_used", 0),
            "Status": "Success" if s.get("tool_success") == 1 else "Failed",
        }
        for i, s in enumerate(step_results)
    ])

    col_w, col_g = st.columns([0.6, 0.4])

    with col_w:
        # Latency Waterfall Bar Chart
        fig_lat = px.bar(
            steps_df,
            x="Step",
            y="Duration (s)",
            color="Status",
            color_discrete_map={"Success": "#10B981", "Failed": "#EF4444"},
            title="⏱️ Step Latency Breakdown (Seconds)",
            text_auto=".2f",
        )
        fig_lat.update_layout(
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            height=260,
        )
        st.plotly_chart(fig_lat, use_container_width=True)

    with col_g:
        # Token Gauge Chart against max_tokens_per_run
        max_budget = settings.max_tokens_per_run
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=total_tokens,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Token Budget Burn", "font": {"size": 16}},
                gauge={
                    "axis": {"range": [0, max_budget], "tickwidth": 1},
                    "bar": {"color": "#6366F1"},
                    "steps": [
                        {"range": [0, max_budget * 0.5], "color": "rgba(16, 185, 129, 0.2)"},
                        {"range": [max_budget * 0.5, max_budget * 0.85], "color": "rgba(245, 158, 11, 0.2)"},
                        {"range": [max_budget * 0.85, max_budget], "color": "rgba(239, 68, 68, 0.2)"},
                    ],
                    "threshold": {
                        "line": {"color": "#EF4444", "width": 3},
                        "thickness": 0.75,
                        "value": max_budget,
                    },
                },
            )
        )
        fig_gauge.update_layout(
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            height=260,
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
