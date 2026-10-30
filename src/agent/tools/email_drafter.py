"""
Email Drafting Tool with Safety Confirmation Gate.

Drafts structured email communications (To, CC, Subject, Body).
Never sends emails over SMTP/network — always appends [DRAFT — NOT SENT]
watermark and marks requires_approval=True (sensitive action).
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.tools import tool

from src.agent.tools.base import ToolResult
from src.config.settings import get_settings


DRAFT_WATERMARK = "=== [DRAFT — NOT SENT] ==="


def draft_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> ToolResult:
    """
    Generate an email draft safely without network transmission.

    Parameters
    ----------
    to : str
        Recipient email address or placeholder.
    subject : str
        Subject line of the email.
    body : str
        Main body text of the message.
    cc : str, optional
        Carbon copy recipients.

    Returns
    -------
    ToolResult
        Standardised tool result with the drafted email text and approval flag.
    """
    start_time = time.perf_counter()
    tool_name = "email_draft"
    settings = get_settings()

    if not to.strip():
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error="Recipient ('to') cannot be empty.",
            duration_s=0.0,
            tokens_used=5,
            requires_approval=True,
        )

    if not subject.strip():
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error="Subject cannot be empty.",
            duration_s=0.0,
            tokens_used=5,
            requires_approval=True,
        )

    lines = [
        DRAFT_WATERMARK,
        f"To: {to.strip()}",
    ]
    if cc and cc.strip():
        lines.append(f"CC: {cc.strip()}")
    lines.extend([
        f"Subject: {subject.strip()}",
        "",
        "Body:",
        body.strip(),
        "",
        "--------------------------------------------------",
        "STATUS: DRAFT SAVED TO EXECUTION LOG",
        "NOTE: Agent is configured in draft-only mode. No email was transmitted.",
        DRAFT_WATERMARK,
    ])

    draft_text = "\n".join(lines)
    duration = time.perf_counter() - start_time

    return ToolResult(
        tool_name=tool_name,
        success=True,
        output=draft_text,
        error=None,
        duration_s=round(duration, 4),
        tokens_used=min(2000, max(30, len(draft_text) // 4)),
        requires_approval=True,  # SENSITIVE: requires human approval
        metadata={
            "to": to,
            "cc": cc,
            "subject": subject,
            "watermarked": True,
            "draft_only_enforced": settings.email_draft_only,
        },
    )


@tool("email_draft")
def email_drafter_tool(to: str, subject: str, body: str, cc: str = "") -> str:
    """
    Draft an email message with recipient, subject, and body.
    Requires human confirmation. NEVER sends actual emails (draft-only).
    """
    res = draft_email(to=to, subject=subject, body=body, cc=cc if cc else None)
    if res.success:
        return res.output
    return f"Error: {res.error}"
