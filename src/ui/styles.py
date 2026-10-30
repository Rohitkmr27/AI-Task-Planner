"""
Enterprise Design System and CSS tokens for Streamlit UI.
"""

ENTERPRISE_CSS = """
<style>
/* Main typography and container spacing */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

code, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Header gradient */
.enterprise-header {
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #60A5FA 0%, #A78BFA 50%, #F472B6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.sub-header-tag {
    font-size: 0.95rem;
    color: #94A3B8;
    margin-bottom: 1.2rem;
    font-weight: 500;
}

/* Glassmorphism metric cards */
.metric-box {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.25);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.metric-box:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.4);
}

.metric-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94A3B8;
    font-weight: 600;
}

.metric-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-top: 0.2rem;
}

/* Step cards */
.step-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    border-left: 4px solid #64748B;
    transition: all 0.2s ease;
}

.step-card-active {
    border-left: 4px solid #3B82F6 !important;
    background: rgba(30, 58, 138, 0.15) !important;
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.15);
}

.step-card-done {
    border-left: 4px solid #10B981 !important;
    background: rgba(6, 78, 59, 0.12) !important;
}

.step-card-failed {
    border-left: 4px solid #EF4444 !important;
    background: rgba(127, 29, 29, 0.15) !important;
}

/* Tool pill badge */
.tool-pill {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    background: rgba(99, 102, 241, 0.18);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.tool-pill-sensitive {
    background: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.35);
}

/* Status indicator pills */
.status-pill {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
}

.status-active {
    background: rgba(59, 130, 246, 0.2);
    color: #60A5FA;
}

.status-completed {
    background: rgba(16, 185, 129, 0.2);
    color: #34D399;
}

.status-failed {
    background: rgba(239, 68, 68, 0.2);
    color: #F87171;
}

.status-awaiting {
    background: rgba(245, 158, 11, 0.2);
    color: #FBBF24;
}

/* Terminal styled output box */
.terminal-output {
    background: #090D16;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #E2E8F0;
    max-height: 280px;
    overflow-y: auto;
}
</style>
"""


def apply_enterprise_theme() -> None:
    """Inject enterprise styling into the active Streamlit page."""
    import streamlit as st
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)
