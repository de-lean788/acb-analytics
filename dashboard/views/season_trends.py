"""
Vista 2 — Tendencia de Temporada
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import io

from dashboard.charts import (
    base_layout, format_pct, format_delta, hex_to_rgba, insight_box,
    ACCENT, BG, BORDER, TEXT, MUTED, POS_CLR, NEG_CLR, WIN_CLR, LOSS_CLR
)


def render(data: dict):
    ff = data["ff"].copy()
    nr = data["nr"].copy()
    ss = data["ss"]

    st.markdown("# Tendencia de Temporada")

    if ff.empty:
        st.warning("Sin datos suficientes.")
        return

    # Labels para el eje X
    rivals_short = ff["rival_name"].apply(_short)
    ff["label"] = [f"J{i+1} {r}\n({'W' if res=='W' else 'L'})"
                   for i, (r, res) in enumerate(zip(rivals_short, ff["result"]))]
    nr["label"] = ff["label"]

    wins  = ss["wins"]
    losses = ss["losses"]
    total = wins + losses

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Balance", f"{wins}V — {losses}D")
    with c2:
        st.metric("Net Rating medio", f"{ss['avg_nrtg']:+.1f}",
                  help="Diferencia entre ataque y defensa por cada 100 posesiones")
    with c3:
        st.metric("ORtg medio", f"{ss['avg_ortg']:.1f}",
                  help="Puntos anotados por cada 100 posesiones")
    with c4:
        st.metric("DRtg medio", f"{ss['avg_drtg']:.1f}",
                  help="Puntos encajados por cada 100 posesiones")
    with c5:
        st.metric("eFG% medio", format_pct(ss["avg_efg"]),
                  help="Eficiencia media de tiro ajustada por triples")

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["NET RATING", "FOUR FACTORS", "MARCADORES"])

    # ── Net Rating ────────────────────────────────────────────────────────────
    with tab1:
        insight_box(
            "<b>Net Rating</b>: diferencia entre los puntos que anota y encaja Bilbao "
            "por cada 100 posesiones. Positivo (amarillo) = el equipo anota más de lo que encaja. "
            "Negativo (rojo) = el rival domina. "
            "<b>ORtg</b> (azul) mide solo el ataque y <b>DRtg</b> (rojo) solo la defensa: "
            "cuanto más separadas estén las líneas, más diferencia hay entre ataque y defensa."
        )

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=nr["label"], y=nr["nrtg"],
            marker_color=[ACCENT if v >= 0 else NEG_CLR for v in nr["nrtg"]],
            marker_line_width=0,
            name="Net Rating",
            hovertemplate="<b>%{x}</b><br>Net Rating: %{y:.1f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=nr["label"], y=nr["ortg"],
            mode="lines+markers", name="ORtg (ataque)",
            line=dict(color="#60a5fa", width=2), marker=dict(size=6),
            hovertemplate="ORtg: %{y:.1f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=nr["label"], y=nr["drtg"],
            mode="lines+markers", name="DRtg (defensa)",
            line=dict(color="#f87171", width=2), marker=dict(size=6),
            hovertemplate="DRtg: %{y:.1f}<extra></extra>",
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)

        layout = base_layout("Net Rating · ORtg (ataque) · DRtg (defensa) por partido",
                             height=440, has_legend=True)
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

        tbl = nr[["label", "score_bilbao", "score_rival",
                  "poss", "ortg", "drtg", "nrtg"]].copy()
        tbl.columns = ["Partido", "Pts Bilbao", "Pts Rival",
                       "Posesiones", "ORtg", "DRtg", "Net Rtg"]
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    # ── Four Factors ──────────────────────────────────────────────────────────
    with tab2:
        insight_box(
            "Los <b>Four Factors</b> (Cuatro Factores) son las cuatro causas principales "
            "que explican por qué un equipo gana o pierde, según el analista Dean Oliver. "
            "En orden de importancia: "
            "<b>eFG%</b> = eficiencia de tiro (el más importante); "
            "<b>TOV%</b> = pérdidas de balón (cuanto más bajo, mejor); "
            "<b>ORB%</b> = rebotes ofensivos capturados; "
            "<b>FT Rate</b> = agresividad para ir a la línea de tiros libres. "
            "Las barras amarillas son victorias, las grises son derrotas."
        )

        factors = [
            ("efg_pct",  "eFG%  —  Eficiencia de tiro",
             "Mide qué tan bien tira el equipo. Un triple puntúa más que un doble, "
             "así que se ajusta. Por encima del 50% es buen nivel.", True),
            ("tov_pct",  "TOV%  —  Pérdidas de balón",
             "Porcentaje de posesiones que terminan en pérdida sin tirar. "
             "Cuanto más bajo, mejor: por debajo del 15% es excelente.", False),
            ("orb_pct",  "ORB%  —  Rebote ofensivo",
             "Porcentaje de rebotes ofensivos capturados. "
             "Un número alto significa segundas oportunidades de anotar.", True),
            ("ft_rate",  "FT Rate  —  Agresividad en tiros libres",
             "Tiros libres intentados respecto a los de campo. "
             "Un valor alto indica que el equipo ataca con agresividad y provoca faltas.", True),
        ]

        col_left, col_right = st.columns(2)
        for i, (col_name, label, desc, higher_better) in enumerate(factors):
            target = col_left if i % 2 == 0 else col_right
            with target:
                vals   = ff[col_name] * 100
                avg    = vals.mean()
                colors = [ACCENT if r == "W" else "#444" for r in ff["result"]]

                fig = go.Figure(go.Bar(
                    x=ff["label"], y=vals,
                    marker_color=colors, marker_line_width=0,
                    hovertemplate=f"<b>%{{x}}</b><br>{col_name.upper()}: %{{y:.1f}}%<extra></extra>",
                ))
                fig.add_hline(y=avg, line_dash="dot", line_color=MUTED,
                              annotation_text=f"Media {avg:.1f}%",
                              annotation_font_color=MUTED,
                              annotation_position="top right")

                layout = base_layout(label, height=270)
                layout["margin"] = dict(l=32, r=80, t=48, b=40)
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)
                st.caption(desc)

        st.markdown("#### Victorias vs Derrotas — perfil medio")
        insight_box(
            "Comparación del perfil Four Factors en los partidos ganados (amarillo) "
            "vs los perdidos (rojo). Cuanto más grande sea el área amarilla respecto "
            "a la roja en cada eje, más diferencia hay en ese factor entre ganar y perder."
        )
        _radar_wl(ff)

    # ── Marcadores ────────────────────────────────────────────────────────────
    with tab3:
        insight_box(
            "Puntos anotados por Bilbao (amarillo) y por el rival (gris) en cada partido. "
            "Cuando la barra amarilla supera a la gris, Bilbao gana. "
            "La diferencia entre ambas barras es el margen de victoria o derrota."
        )

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=nr["label"], y=nr["score_bilbao"],
            name="Bilbao", marker_color=ACCENT, marker_line_width=0,
        ))
        fig.add_trace(go.Bar(
            x=nr["label"], y=nr["score_rival"],
            name="Rival", marker_color="#444", marker_line_width=0,
        ))
        layout = base_layout("Puntos anotados por partido", height=400, has_legend=True)
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        buf = io.StringIO()
        nr.drop(columns=["label"], errors="ignore").to_csv(buf, index=False)
        st.download_button("⬇  Net Ratings (CSV)", buf.getvalue(),
                           "bilbao_net_ratings.csv", "text/csv", use_container_width=True)
    with col2:
        buf2 = io.StringIO()
        ff.drop(columns=["label"], errors="ignore").to_csv(buf2, index=False)
        st.download_button("⬇  Four Factors (CSV)", buf2.getvalue(),
                           "bilbao_four_factors.csv", "text/csv", use_container_width=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _short(name: str) -> str:
    abbrs = {
        "JoventutBadalona": "JOV", "MoraBancAndorra": "AND",
        "BAXIManresa": "MAN", "CasademontZaragoza": "ZAR",
        "RealMadrid": "RMA", "KosnerBaskonia": "BAS",
        "DreamlandGranCanaria": "GCA", "HioposLleida": "LLE",
        "RioBreogan": "BRE", "Bara": "BAR", "ValenciaBasket": "VAL",
        "BsquetGirona": "GIR", "UCAMMurcia": "MUR",
        "LaLagunaTenerife": "TEN", "CoviranGranada": "GRA",
        "RecoletasSalud": "BUR", "RecoletasSaludSanPabloBurgos": "BUR",
    }
    for k, v in abbrs.items():
        if k.lower() in name.lower():
            return v
    return name[:3].upper()


def _radar_wl(ff):
    factors = ["efg_pct", "orb_pct", "ft_rate"]
    labels  = ["eFG%", "ORB%", "FT Rate"]

    wins   = ff[ff["result"] == "W"]
    losses = ff[ff["result"] == "L"]

    if wins.empty or losses.empty:
        st.caption("Se necesitan victorias Y derrotas para este gráfico.")
        return

    fig = go.Figure()
    for grp, color, name in [
        (wins,   ACCENT,    "Victorias"),
        (losses, "#f87171", "Derrotas"),
    ]:
        vals = [grp[f].mean() * 100 for f in factors] 
        vals += [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=labels + [labels[0]],
            fill="toself",
            fillcolor=hex_to_rgba(color, 0.15),
            line=dict(color=color, width=2),
            name=name,
        ))

    fig.update_layout(
        polar=dict(
            bgcolor=BG,
            radialaxis=dict(visible=True, range=[0, 70],
                            gridcolor=BORDER, linecolor=BORDER,
                            tickfont=dict(size=10, color=MUTED)),
            angularaxis=dict(gridcolor=BORDER, linecolor=BORDER),
        ),
        paper_bgcolor=BG,
        font=dict(family="DM Mono, monospace", color=TEXT),
        legend=dict(font=dict(size=11, color=TEXT), orientation="h", y=-0.15),
        height=340,
        margin=dict(l=48, r=48, t=24, b=48),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)
