"""
Vista 4 — Análisis de Rival
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import io

from dashboard.charts import (
    base_layout, hex_to_rgba, insight_box,
    ACCENT, BG, BORDER, TEXT, MUTED, NEG_CLR, WIN_CLR, LOSS_CLR
)


def render(data: dict):
    ff  = data["ff"].copy()
    nr  = data["nr"].copy()

    st.markdown("# Análisis de Rival")

    if ff.empty:
        st.warning("Sin datos de partidos.")
        return

    insight_box(
        "Selecciona un partido para ver cómo rindió Bilbao en ese enfrentamiento. "
        "Útil para preparar la revancha: identificar qué factores fallaron "
        "y en qué mejoró el equipo respecto a su media habitual."
    )

    rivals = ff["rival_name"].tolist()
    dates  = [f"{r[:4]}-{r[4:6]}-{r[6:]}" for r in ff["date"].tolist()]

    selected = st.selectbox(
        "Selecciona el partido",
        options=range(len(rivals)),
        format_func=lambda i: (
            f"{dates[i]}  ·  vs {rivals[i]}  ·  "
            f"{'✓' if ff.iloc[i]['result']=='W' else '✗'}  "
            f"{int(ff.iloc[i]['score_bilbao'])}-{int(ff.iloc[i]['score_rival'])}"
        ),
    )

    row_ff = ff.iloc[selected]
    row_nr = nr.iloc[selected]
    rc     = WIN_CLR if row_ff["result"] == "W" else LOSS_CLR
    result_word = "VICTORIA" if row_ff["result"] == "W" else "DERROTA"

    st.markdown(f"""
    <div style="border-left:4px solid {rc};padding:12px 20px;margin:16px 0;
                background:#111;border-radius:0 4px 4px 0;">
        <span style="font-family:'Syne';font-size:20px;font-weight:700;color:{TEXT};">
            vs {row_ff['rival_name']}
        </span>
        &nbsp;&nbsp;
        <span style="font-family:'DM Mono';font-size:24px;font-weight:500;color:{rc};">
            {int(row_ff['score_bilbao'])} — {int(row_ff['score_rival'])}
            &nbsp;·&nbsp; {result_word}
        </span>
        &nbsp;&nbsp;
        <span style="font-family:'DM Mono';font-size:12px;color:{MUTED};">
            ORtg {row_nr['ortg']:.1f} · DRtg {row_nr['drtg']:.1f} · Net {row_nr['nrtg']:+.1f}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Four Factors comparativa ──────────────────────────────────────────────
    st.markdown("#### Cuatro Factores: este partido vs media de temporada")
    insight_box(
        "Cada métrica compara el rendimiento en este partido respecto al promedio "
        "de toda la temporada. La flecha verde indica que estuvimos mejor de lo habitual; "
        "la roja, peor. En <b>TOV%</b> la flecha verde significa menos pérdidas (mejor). "
        "Identifica rápidamente los factores que decidieron este partido."
    )

    factors = [
        ("efg_pct", "eFG%",    True,  "Eficiencia de tiro. Por encima del 50% es buen nivel."),
        ("tov_pct", "TOV%",    False, "% de posesiones perdidas. Cuanto más bajo, mejor."),
        ("orb_pct", "ORB%",    True,  "% de rebotes ofensivos capturados."),
        ("ft_rate", "FT Rate", True,  "Tiros libres intentados / tiros de campo intentados."),
    ]
    cols = st.columns(4)
    for i, (col_name, label, higher_better, desc) in enumerate(factors):
        val   = row_ff[col_name]
        avg   = ff[col_name].mean()
        delta = val - avg
        better = (delta >= 0 and higher_better) or (delta < 0 and not higher_better)
        with cols[i]:
            st.metric(label, f"{val*100:.1f}%",
                      delta=f"{delta*100:+.1f}pp vs media",
                      delta_color="normal" if better else "inverse",
                      help=desc)

    st.markdown("<br>", unsafe_allow_html=True)

    col_radar, col_table = st.columns([1, 1])

    with col_radar:
        _four_factors_radar(row_ff, ff)

    with col_table:
        st.markdown("#### Todos los enfrentamientos")
        st.caption("FF Score: índice compuesto de los cuatro factores. Más alto = mejor rendimiento global.")
        tbl = ff[["date","rival_name","result","score_bilbao","score_rival",
                   "efg_pct","tov_pct","orb_pct","ft_rate","ff_score"]].copy()
        tbl["date"]    = tbl["date"].apply(lambda d: f"{d[:4]}-{d[4:6]}-{d[6:]}")
        tbl["efg_pct"] = tbl["efg_pct"].apply(lambda v: f"{v*100:.1f}%")
        tbl["tov_pct"] = tbl["tov_pct"].apply(lambda v: f"{v*100:.1f}%")
        tbl["orb_pct"] = tbl["orb_pct"].apply(lambda v: f"{v*100:.1f}%")
        tbl["ft_rate"]  = tbl["ft_rate"].apply(lambda v: f"{v*100:.0f}%")
        tbl["ff_score"] = tbl["ff_score"].apply(lambda v: f"{v:.3f}")
        tbl.columns = ["Fecha","Rival","Res.","Pts B","Pts R",
                       "eFG%","TOV%","ORB%","FTr","FF Score"]

        def _cr(val):
            if val == "W":
                return f"color:{WIN_CLR};font-weight:600"
            return f"color:#f87171;font-weight:600"

        st.dataframe(tbl.style.applymap(_cr, subset=["Res."]),
                     use_container_width=True, hide_index=True)

    # ── FF Score por partido ──────────────────────────────────────────────────
    st.markdown("#### FF Score por partido")
    insight_box(
        "<b>FF Score</b> es un índice que combina los cuatro factores en un solo número: "
        "cuanto más alto, mejor fue el rendimiento global del equipo en ese partido. "
        "Valores por encima de 0.30 suelen asociarse a victorias; "
        "por debajo de 0.27 suelen ser derrotas."
    )

    ff["label_short"] = ff["rival_name"].apply(lambda n: n[:3].upper())
    fig = go.Figure(go.Bar(
        x=ff["label_short"], y=ff["ff_score"],
        marker_color=[ACCENT if r == "W" else "#444" for r in ff["result"]],
        marker_line_width=0,
        text=[f"{'W' if r=='W' else 'L'}" for r in ff["result"]],
        textposition="outside",
        textfont=dict(size=11, color=TEXT),
        hovertemplate="<b>%{x}</b><br>FF Score: %{y:.3f}<extra></extra>",
    ))
    avg_score = ff["ff_score"].mean()
    fig.add_hline(y=avg_score, line_dash="dot", line_color=MUTED,
                  annotation_text=f"Media {avg_score:.3f}",
                  annotation_font_color=MUTED, annotation_position="top right")
    layout = base_layout("FF Score por partido  —  amarillo = victoria, gris = derrota",
                         height=320)
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.markdown("---")
    buf = io.StringIO()
    ff.drop(columns=["label", "label_short"], errors="ignore").to_csv(buf, index=False)
    st.download_button("⬇  Four Factors todos los partidos (CSV)",
                       buf.getvalue(), "bilbao_four_factors_all.csv", "text/csv")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _four_factors_radar(row_ff, ff):
    factors = ["efg_pct", "orb_pct", "ft_rate"]
    labels  = ["eFG%", "ORB%", "FT Rate"]
    this    = [row_ff[f] * 100 for f in factors]
    season  = [ff[f].mean() * 100 for f in factors]
    rc      = WIN_CLR if row_ff["result"] == "W" else LOSS_CLR

    fig = go.Figure()
    for vals, color, name in [
        (season + [season[0]], MUTED, "Media temporada"),
        (this   + [this[0]],   rc,    f"vs {row_ff['rival_name']}"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=labels + [labels[0]],
            fill="toself", fillcolor=hex_to_rgba(color, 0.13),
            line=dict(color=color, width=2), name=name,
        ))

    fig.update_layout(
        polar=dict(
            bgcolor=BG,
            radialaxis=dict(range=[0, 70], gridcolor=BORDER,
                            tickfont=dict(size=10, color=MUTED)),
            angularaxis=dict(gridcolor=BORDER),
        ),
        paper_bgcolor=BG,
        font=dict(family="DM Mono, monospace", color=TEXT),
        legend=dict(font=dict(size=11, color=TEXT), orientation="h", y=-0.15),
        height=340, margin=dict(l=40, r=40, t=24, b=48),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)
