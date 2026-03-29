"""
Vista 1 — Impacto de Jugadores
On/Off splits + shooting profile + lineups
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import io

from dashboard.charts import (
    base_layout, bar_colors, format_pct, insight_box,
    ACCENT, BG, BORDER, TEXT, MUTED, POS_CLR, NEG_CLR, WIN_CLR
)


def render(data: dict):
    pi = data["pi"].copy()
    ls = data["ls"].copy()
    sp = data["sp"].copy()

    st.markdown("# Impacto de Jugadores")

    if pi.empty:
        st.warning("No hay datos de lineups. Ejecuta `rebuild_lineups()` primero.")
        return

    # ── KPIs top row ──────────────────────────────────────────────────────────
    best        = pi.iloc[0]
    worst       = pi[pi["on_off_diff"].notna()].iloc[-1]
    best_efg    = sp.sort_values("efg_pct", ascending=False).iloc[0]
    best_scorer = sp.sort_values("pts_per_game", ascending=False).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Mayor impacto ON/OFF", best["player_name"],
                  delta=f"{int(best['on_off_diff']):+d} pts")
    with c2:
        st.metric("Menor impacto ON/OFF", worst["player_name"],
                  delta=f"{int(worst['on_off_diff']):+d} pts", delta_color="inverse")
    with c3:
        st.metric("Tiro más eficiente", best_efg["player_name"],
                  delta=format_pct(best_efg["efg_pct"]))
    with c4:
        st.metric("Top anotador", best_scorer["player_name"],
                  delta=f"{best_scorer['pts_per_game']:.1f} pts/partido")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["ON/OFF SPLITS", "PERFIL DE TIRO", "MEJORES QUINTETOS"])

    # ── Tab 1: On/Off ─────────────────────────────────────────────────────────
    with tab1:
        insight_box(
            "El <b>diferencial ON/OFF</b> mide cuántos puntos gana o pierde el equipo "
            "con cada jugador en pista respecto a cuando está en el banquillo. "
            "Una barra amarilla (ON) alta significa que el equipo funciona mejor cuando ese jugador juega. "
            "Una barra gris (OFF) muy negativa indica que el equipo sufre en su ausencia. "
            "El jugador ideal tiene ON alto y OFF bajo."
        )

        col_chart, col_table = st.columns([3, 2])

        with col_chart:
            pi_sorted = pi.sort_values("on_off_diff", ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=pi_sorted["player_name"],
                x=pi_sorted["net_pts_on"],
                name="En pista (ON)",
                orientation="h",
                marker_color=ACCENT,
                marker_line_width=0,
            ))
            fig.add_trace(go.Bar(
                y=pi_sorted["player_name"],
                x=pi_sorted["net_pts_off"],
                name="En banquillo (OFF)",
                orientation="h",
                marker_color="#555",
                marker_line_width=0,
            ))
            layout = base_layout("Puntos netos con el jugador en pista vs en banquillo",
                                 height=420, has_legend=True)
            layout["barmode"] = "group"
            layout["xaxis"]["title"] = "Puntos netos acumulados en temporada"
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.markdown("#### Detalle por jugador")
            st.caption("Dif. = ON menos OFF. Verde: el equipo va mejor con él. Rojo: al revés.")
            display = pi[["player_name", "stints_on", "net_pts_on",
                           "net_pts_off", "on_off_diff"]].copy()
            display.columns = ["Jugador", "Entradas", "Pts ON", "Pts OFF", "Dif."]
            display = display.sort_values("Dif.", ascending=False)

            def color_diff(val):
                if pd.isna(val):
                    return ""
                color = "#1a3a1a" if val >= 0 else "#3a1a1a"
                text  = "#4ade80" if val >= 0 else "#f87171"
                return f"background-color: {color}; color: {text}; font-weight: 500"

            styled = display.style.applymap(color_diff, subset=["Dif."])
            st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Tab 2: Shooting profile ───────────────────────────────────────────────
    with tab2:
        insight_box(
            "<b>eFG%</b> (eje horizontal) mide la eficiencia real de tiro: "
            "un triple vale más que un doble, así que se pondera en consecuencia. "
            "Por encima de la línea de puntos = mejor que la media del equipo. "
            "<b>TS%</b> (color del punto) añade los tiros libres al cálculo: cuanto más amarillo, "
            "más eficiente en todas las formas de anotar. "
            "<b>Tamaño del punto</b> = cuántos tiros intenta por partido."
        )

        col_scatter, col_bars = st.columns([3, 2])

        with col_scatter:
            sp_filtered = sp[sp["fga"] > 0].copy()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sp_filtered["efg_pct"] * 100,
                y=sp_filtered["pts_per_game"],
                mode="markers+text",
                text=sp_filtered["player_name"].str.split().str[-1],
                textposition="top center",
                textfont=dict(size=10, color=TEXT),
                marker=dict(
                    size=sp_filtered["fga"].clip(lower=5) / 2,
                    color=sp_filtered["ts_pct"],
                    colorscale=[[0, "#333"], [0.5, "#888"], [1, ACCENT]],
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="TS%", font=dict(size=11)),
                        tickformat=".0%",
                        thickness=10,
                        len=0.6,
                    ),
                    line=dict(width=0),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "eFG%: %{x:.1f}%<br>"
                    "Pts/partido: %{y:.1f}<br>"
                    "<extra></extra>"
                ),
            ))
            avg_efg = (sp_filtered["efg_pct"] * 100).mean()
            fig.add_vline(x=avg_efg, line_dash="dot", line_color=MUTED,
                          annotation_text=f"Media equipo {avg_efg:.1f}%",
                          annotation_font_color=MUTED)

            layout = base_layout("Eficiencia de tiro (eFG%) vs Puntos anotados por partido",
                                 height=420)
            layout["xaxis"]["title"] = "eFG%  —  Eficiencia de tiro ajustada"
            layout["yaxis"]["title"] = "Puntos por partido"
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

        with col_bars:
            st.markdown("#### Tabla de eficiencia")
            st.caption("eFG%: tiro ajustado · TS%: eficiencia total · 3PAr: % triples sobre total tiros · FTr: agresividad en TL")
            cols_show = ["player_name", "games", "pts_per_game",
                         "efg_pct", "ts_pct", "3par", "ft_rate",
                         "ast_per_game", "tov_per_game"]
            labels = ["Jugador", "PJ", "Pts", "eFG%", "TS%", "3PAr", "FTr", "Ast", "Perd"]
            tbl = sp[cols_show].copy()
            tbl.columns = labels
            tbl["eFG%"] = tbl["eFG%"].apply(lambda x: f"{x*100:.1f}%")
            tbl["TS%"]  = tbl["TS%"].apply(lambda x: f"{x*100:.1f}%")
            tbl["3PAr"] = tbl["3PAr"].apply(lambda x: f"{x*100:.0f}%")
            tbl["FTr"]  = tbl["FTr"].apply(lambda x: f"{x*100:.0f}%")
            tbl = tbl.sort_values("Pts", ascending=False)
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    # ── Tab 3: Lineups ────────────────────────────────────────────────────────
    with tab3:
        insight_box(
            "Cada fila es un <b>quinteto</b> que ha jugado juntos en dos o más momentos del partido. "
            "Los <b>Pts netos</b> muestran cuántos puntos ha ganado o perdido el equipo mientras ese "
            "grupo estaba en pista: amarillo = el equipo va por delante cuando juegan, "
            "rojo = el rival remonta. <b>Entradas</b> indica cuántas veces ha salido ese quinteto a pista."
        )

        if ls.empty:
            st.info("No hay quintetos con 2+ apariciones todavía. Con más partidos aparecerán aquí.")
        else:
            player_cols = ["p1_name", "p2_name", "p3_name", "p4_name", "p5_name"]
            ls["Quinteto"] = ls[player_cols].apply(
                lambda r: " · ".join(n.split()[-1] for n in r if pd.notna(n)), axis=1
            )
            ls_display = ls[["Quinteto", "stints", "net_pts", "net_per_stint"]].copy()
            ls_display.columns = ["Quinteto", "Entradas", "Pts netos", "Pts/entrada"]

            fig = go.Figure(go.Bar(
                y=ls_display["Quinteto"],
                x=ls_display["Pts netos"],
                orientation="h",
                marker_color=[ACCENT if v >= 0 else NEG_CLR for v in ls_display["Pts netos"]],
                marker_line_width=0,
                text=ls_display["Entradas"].apply(lambda s: f"{s}x"),
                textposition="outside",
                textfont=dict(size=10, color=MUTED),
            ))
            layout = base_layout("Puntos netos acumulados por quinteto",
                                 height=max(300, len(ls) * 50))
            layout["xaxis"]["title"] = "Puntos netos (positivo = Bilbao domina, negativo = rival domina)"
            layout["margin"]["l"] = 240
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(ls_display, use_container_width=True, hide_index=True)

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        buf = io.StringIO()
        pi[["player_name","stints_on","stints_off","net_pts_on",
            "net_pts_off","on_off_diff","games","pts_per_game",
            "efg_pct","ts_pct","ast_per_game","tov_per_game"]].to_csv(buf, index=False)
        st.download_button("⬇  Descargar On/Off (CSV)", buf.getvalue(),
                           "bilbao_player_impact.csv", "text/csv",
                           use_container_width=True)
    with col2:
        buf2 = io.StringIO()
        sp.drop(columns=["fga"], errors="ignore").to_csv(buf2, index=False)
        st.download_button("⬇  Descargar Perfil de Tiro (CSV)", buf2.getvalue(),
                           "bilbao_shooting_profile.csv", "text/csv",
                           use_container_width=True)
