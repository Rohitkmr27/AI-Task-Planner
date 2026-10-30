"""
Unit tests for Streamlit UI components and page modules.
"""

from __future__ import annotations

import importlib
import pytest


def test_ui_components_import():
    """Verify that all UI components import cleanly."""
    from src.ui.components.export_tools import render_export_buttons
    from src.ui.components.plan_editor import render_plan_editor
    from src.ui.components.plan_viewer import render_plan, TOOL_ICONS
    from src.ui.components.telemetry_viewer import render_telemetry
    from src.ui.components.trace_viewer import render_trace
    from src.ui.styles import apply_enterprise_theme

    assert "calc" in TOOL_ICONS
    assert callable(render_plan)
    assert callable(render_trace)
    assert callable(render_plan_editor)
    assert callable(render_telemetry)
    assert callable(render_export_buttons)
    assert callable(apply_enterprise_theme)


def test_ui_pages_import():
    """Verify that all Streamlit page scripts have valid syntax and import cleanly."""
    app_module = importlib.import_module("src.ui.app")
    assert hasattr(app_module, "main")

    # Import page modules to ensure no syntax/import errors
    importlib.import_module("src.ui.pages.1_Task_Planner")
    importlib.import_module("src.ui.pages.2_Execution_Logs")
    importlib.import_module("src.ui.pages.3_EDA_Dashboard")
