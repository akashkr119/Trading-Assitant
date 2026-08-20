"""Shared responsive visual system for all Trading Assistant Streamlit pages."""

import streamlit as st

CSS = """
<style>
:root {
  --ta-bg: #080B12;
  --ta-surface: #0F141D;
  --ta-card: #151B26;
  --ta-border: #273142;
  --ta-text: #F4F7FB;
  --ta-muted: #8E9AAF;
  --ta-gold: #D6A84F;
  --ta-cyan: #29D3E6;
  --ta-green: #22C55E;
  --ta-red: #F04444;
  --ta-amber: #F59E0B;
  --ta-purple: #8B7CFF;
}

.stApp {
  background: radial-gradient(circle at top right, rgba(41, 211, 230, .055), transparent 34%), var(--ta-bg);
  color: var(--ta-text);
}

.block-container {
  max-width: 1500px;
  padding-top: clamp(1rem, 2vw, 2rem);
  padding-left: clamp(.8rem, 2vw, 2.5rem);
  padding-right: clamp(.8rem, 2vw, 2.5rem);
  padding-bottom: 3rem;
}

h1, h2, h3, h4, h5, h6, p, label, [data-testid="stMetricLabel"],
[data-testid="stMetricValue"], .stMarkdown, .stCaption {
  overflow-wrap: anywhere;
  word-break: normal;
}

h1 { font-size: clamp(1.55rem, 2.5vw, 2.15rem) !important; }
h2 { font-size: clamp(1.25rem, 2vw, 1.65rem) !important; }
h3 { font-size: clamp(1.05rem, 1.5vw, 1.3rem) !important; }

[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(21,27,38,.96), rgba(15,20,29,.96));
  border: 1px solid var(--ta-border);
  border-radius: 14px;
  padding: .8rem .9rem;
  min-height: 92px;
}

[data-testid="stMetricLabel"] {
  color: var(--ta-muted) !important;
  font-size: clamp(.72rem, 1vw, .84rem) !important;
}
[data-testid="stMetricValue"] {
  color: var(--ta-text) !important;
  font-size: clamp(1.15rem, 2vw, 1.7rem) !important;
}

.stButton > button, .stDownloadButton > button {
  border-radius: 10px;
  min-height: 42px;
  font-weight: 650;
  white-space: normal;
  overflow-wrap: anywhere;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--ta-border);
  border-radius: 12px;
  overflow: hidden;
}

div[data-testid="stExpander"] {
  border: 1px solid var(--ta-border);
  border-radius: 12px;
  background: rgba(15,20,29,.65);
}

[data-testid="stDataFrame"] > div { max-width: 100%; overflow-x: auto; }

@media (max-width: 768px) {
  .block-container { padding-left: .65rem; padding-right: .65rem; }
  [data-testid="stHorizontalBlock"] { gap: .45rem; }
  [data-testid="stMetric"] { min-height: 78px; padding: .65rem .7rem; }
  [data-testid="stMetricValue"] { line-height: 1.15; }
  .stButton > button { min-height: 44px; }
}

@media (max-width: 480px) {
  .block-container { padding-left: .5rem; padding-right: .5rem; }
  [data-testid="stMetricLabel"] { font-size: .7rem !important; }
  [data-testid="stMetricValue"] { font-size: 1.05rem !important; }
  .stCaption, [data-testid="stCaptionContainer"] { font-size: .72rem; }
}
</style>
"""


def apply_theme() -> None:
    """Apply the shared responsive dark fintech theme."""
    st.markdown(CSS, unsafe_allow_html=True)


def inject_responsive_css() -> None:
    """Backward-compatible alias used by existing Streamlit pages."""
    apply_theme()


def page_header(title: str, subtitle: str = "", accent: str = "gold") -> None:
    """Render a consistent page header."""
    accent_colors = {
        "gold": "#D6A84F",
        "cyan": "#29D3E6",
        "green": "#22C55E",
        "red": "#F04444",
        "amber": "#F59E0B",
        "purple": "#8B7CFF",
    }
    color = accent_colors.get(accent, accent_colors["gold"])
    st.markdown(
        f'<div style="border-left:4px solid {color}; padding:.25rem 0 .35rem .8rem; margin-bottom:1rem;">'
        f'<h1 style="margin:0;">{title}</h1>'
        f'<div style="color:var(--ta-muted); margin-top:.2rem;">{subtitle}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a compact section heading."""
    st.markdown(f"### {title}")
