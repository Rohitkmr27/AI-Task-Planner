"""
Base types and models for the Agentic AI Task Planner tools.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Standardised result returned by every tool invocation.

    Ensures consistent recording in execution logs, UI display,
    and agent state tracking.
    """

    tool_name: str = Field(description="Name of the tool that executed.")
    success: bool = Field(description="Whether the tool execution succeeded.")
    output: str = Field(default="", description="Output string or payload from the tool.")
    error: Optional[str] = Field(default=None, description="Error message if execution failed.")
    duration_s: float = Field(default=0.0, ge=0.0, description="Execution duration in seconds.")
    tokens_used: int = Field(default=0, ge=0, description="Estimated or actual tokens used.")
    requires_approval: bool = Field(
        default=False,
        description="Whether this tool requires human-in-the-loop approval before executing.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional auxiliary data (e.g. file paths, status codes, chart objects).",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump()
