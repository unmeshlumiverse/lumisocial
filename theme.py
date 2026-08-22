"""
Shared theme tokens for the LUMISOCIAL dashboard (app.py, brief.py).

Two palettes (DARK / LIGHT) hold the same variable names so the rest of the
app never branches on theme itself — it just reads `var(--...)` in CSS or
`plot_theme()` in Python. Semantic colors (accent/positive/negative/neutral/
critical/info) are deliberately identical across both palettes; only surface,
text, border and shadow values change.
"""

import streamlit as st

_SEMANTIC = {
    "accent": "#0d9488",
    "accent-dark": "#0f766e",
    "accent-light": "#ccfbf1",
    "accent-glow": "rgba(13, 148, 136, 0.25)",
    "pos": "#10b981",
    "pos-bg": "rgba(16, 185, 129, 0.1)",
    "pos-border": "#059669",
    "neg": "#ef4444",
    "neg-bg": "rgba(239, 68, 68, 0.1)",
    "neg-border": "#dc2626",
    "neu": "#f59e0b",
    "neu-bg": "rgba(245, 158, 11, 0.1)",
    "neu-border": "#d97706",
    "info": "#0284c7",
    "info-bg": "rgba(2, 132, 199, 0.1)",
    "critical": "#f59e0b",
    "critical-bg": "rgba(245, 158, 11, 0.1)",
    "positive": "#10b981",
    "negative": "#ef4444",
    "neutral": "#94a3b8",
    "r-sm": "8px",
    "r-md": "12px",
    "r-lg": "16px",
}

DARK = {
    **_SEMANTIC,
    "bg": "#0f172a",
    "surface": "#1e293b",
    "surface-2": "#334155",
    "surface-glass": "rgba(30, 41, 59, 0.45)",
    "border": "#38455a",
    "border-soft": "#475569",
    "text": "#f8fafc",
    "text-2": "#cbd5e1",
    "text-mute": "#94a3b8",
    "shadow-1": "0 4px 10px rgba(0,0,0,0.3)",
    "shadow-2": "0 10px 25px rgba(0,0,0,0.5)",
    "shadow-panel": "0 20px 45px -25px rgba(0,0,0,0.75)",
    "plot-text": "#e2e8f0",
    "plot-grid": "rgba(255,255,255,0.06)",
}

LIGHT = {
    **_SEMANTIC,
    "bg": "#f4f6fb",
    "surface": "#ffffff",
    "surface-2": "#eef1f8",
    "surface-glass": "rgba(255, 255, 255, 0.65)",
    "border": "#d8dee9",
    "border-soft": "#c3cbdb",
    "text": "#0f172a",
    "text-2": "#334155",
    "text-mute": "#64748b",
    "shadow-1": "0 4px 10px rgba(15,23,42,0.06)",
    "shadow-2": "0 10px 25px rgba(15,23,42,0.10)",
    "shadow-panel": "0 20px 45px -30px rgba(15,23,42,0.25)",
    "plot-text": "#1e293b",
    "plot-grid": "rgba(15,23,42,0.08)",
}

PALETTES = {"dark": DARK, "light": LIGHT}


def get_mode() -> str:
    """Current theme mode for this session ('dark' or 'light')."""
    return st.session_state.get("ui_theme", "dark")


def set_mode(mode: str) -> None:
    st.session_state["ui_theme"] = mode if mode in PALETTES else "dark"


def css_vars(mode: str = None) -> str:
    """Render the `:root { --name: value; ... }` block for the given mode."""
    tokens = PALETTES.get(mode or get_mode(), DARK)
    lines = "\n".join(f"        --{k}: {v};" for k, v in tokens.items())
    return f":root {{\n{lines}\n    }}"


def plot_theme(mode: str = None) -> dict:
    """Font/gridline colors for Plotly figures, matching the active theme."""
    tokens = PALETTES.get(mode or get_mode(), DARK)
    return {"text": tokens["plot-text"], "grid": tokens["plot-grid"]}
