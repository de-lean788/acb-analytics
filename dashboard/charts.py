"""
Helpers de visualización compartidos entre vistas.
"""

import plotly.graph_objects as go
import pandas as pd

# ── Paleta ────────────────────────────────────────────────────────────────────
ACCENT   = "#e8ff00"
BG       = "#0d0d0d"
SURFACE  = "#111111"
BORDER   = "#222222"
TEXT     = "#e0e0e0"
MUTED    = "#555555"
WIN_CLR  = "#e8ff00"
LOSS_CLR = "#444444"
POS_CLR  = "#e8ff00"
NEG_CLR  = "#ff4444"


def base_layout(title: str = "", height: int = 380, has_legend: bool = False) -> dict:
    """
    Layout base para todos los gráficos.
    has_legend=True reserva espacio extra arriba para que la leyenda
    no tape el título.
    """
    top_margin = 80 if has_legend else 48
    layout = dict(
        title=dict(
            text=title,
            font=dict(family="Syne, sans-serif", size=13, color=TEXT),
            y=0.98, yanchor="top", x=0, xanchor="left",
        ),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="DM Mono, monospace", size=12, color=TEXT),
        height=height,
        margin=dict(l=48, r=24, t=top_margin, b=48),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(size=11)),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(size=11)),
        showlegend=has_legend,
    )
    if has_legend:
        layout["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.06,
            xanchor="left",
            x=0,
            font=dict(size=11, color=TEXT),
            bgcolor="rgba(0,0,0,0)",
        )
    return layout


def result_color(result: str) -> str:
    return WIN_CLR if result == "W" else LOSS_CLR


def bar_colors(values: pd.Series) -> list:
    return [POS_CLR if v >= 0 else NEG_CLR for v in values]


def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    """Convierte '#rrggbb' a 'rgba(r,g,b,alpha)' correctamente."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def format_pct(val: float) -> str:
    return f"{val*100:.1f}%"


def format_delta(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}"


def insight_box(text: str) -> None:
    """
    Renderiza un bloque de contexto/interpretación inline en Streamlit.
    Usar directamente: insight_box("Texto explicativo...")
    """
    import streamlit as st
    st.markdown(f"""
    <div style="
        border-left: 3px solid {MUTED};
        padding: 10px 16px;
        margin: 4px 0 20px 0;
        background: #161616;
        border-radius: 0 4px 4px 0;
        font-family: 'DM Mono', monospace;
        font-size: 12px;
        color: #999;
        line-height: 1.7;
    ">💡&nbsp;&nbsp;{text}</div>
    """, unsafe_allow_html=True)
