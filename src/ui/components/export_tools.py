"""
Enterprise Audit and Report Exporter Component.

Provides one-click downloads for execution trace JSON, audit CSV,
and executive Markdown reports.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
import pandas as pd
import streamlit as st


def render_export_buttons(
    run_id: str,
    user_goal: str,
    plan: list[dict[str, Any]],
    step_results: list[dict[str, Any]],
    final_result: str | None,
    total_tokens: int,
    total_duration: float,
) -> None:
    """
    Render download buttons for Audit JSON, Step Metrics CSV, and Executive Report Markdown.
    """
    st.markdown("### 💾 Enterprise Audit & Export")

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Full Audit Trace (JSON)
    trace_payload = {
        "run_id": run_id,
        "timestamp_utc": now_iso,
        "user_goal": user_goal,
        "plan": plan,
        "execution_steps": step_results,
        "final_result": final_result,
        "metrics": {
            "total_steps": len(step_results),
            "total_tokens": total_tokens,
            "total_duration_s": total_duration,
        },
    }
    json_bytes = json.dumps(trace_payload, indent=2).encode("utf-8")

    # 2. Executive Report (Markdown)
    report_lines = [
        f"# Executive Task Execution Report",
        f"**Run ID:** `{run_id}` | **Generated:** {now_iso}",
        "",
        f"## 1. Objective",
        user_goal,
        "",
        f"## 2. Summary Metrics",
        f"- **Execution Status:** COMPLETED",
        f"- **Total Steps Executed:** {len(step_results)}",
        f"- **Total Wall-Clock Latency:** {total_duration:.2f} seconds",
        f"- **Total LLM / Tool Tokens:** {total_tokens:,}",
        "",
        f"## 3. Step-by-Step Audit Trail",
    ]
    for s in step_results:
        success_str = "SUCCESS" if s.get("tool_success") == 1 else "FAILED"
        report_lines.append(f"### Step {s.get('step_order')}: {s.get('tool_called')} [{success_str}]")
        report_lines.append(f"- **Duration:** {s.get('duration_s', 0):.2f}s | **Tokens:** {s.get('tokens_used', 0)}")
        report_lines.append(f"```text\n{s.get('tool_output') or s.get('error_message') or '(No output)'}\n```\n")

    if final_result:
        report_lines.extend([
            "## 4. Final Synthesized Result",
            final_result,
        ])

    md_content = "\n".join(report_lines).encode("utf-8")

    # 3. Steps CSV
    steps_df = pd.DataFrame(step_results)
    csv_bytes = steps_df.to_csv(index=False).encode("utf-8")

    col_j, col_m, col_c = st.columns(3)
    with col_j:
        st.download_button(
            label="📥 Download Audit Trace (JSON)",
            data=json_bytes,
            file_name=f"audit_trace_{run_id}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_m:
        st.download_button(
            label="📄 Download Executive Report (MD)",
            data=md_content,
            file_name=f"executive_report_{run_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_c:
        st.download_button(
            label="📊 Download Step Metrics (CSV)",
            data=csv_bytes,
            file_name=f"step_metrics_{run_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )
