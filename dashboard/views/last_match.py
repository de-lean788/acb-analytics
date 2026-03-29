"""
Vista 3 — Resumen del Último Partido
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import io
import os

from db.models import get_engine
from analytics.metrics import boxscore_bilbao
from dashboard.charts import (
    base_layout, hex_to_rgba, insight_box,
    ACCENT, BG, BORDER, TEXT, MUTED, NEG_CLR, WIN_CLR, LOSS_CLR
)


def render(data: dict):
    ff = data["ff"].copy()
    nr = data["nr"].copy()

    st.markdown("# Último Partido")

    if ff.empty:
        st.warning("Sin datos.")
        return

    last_ff = ff.iloc[-1]
    last_nr = nr.iloc[-1]

    rc          = WIN_CLR if last_ff["result"] == "W" else LOSS_CLR
    result_text = "VICTORIA" if last_ff["result"] == "W" else "DERROTA"
    fecha       = f"{last_ff['date'][:4]}-{last_ff['date'][4:6]}-{last_ff['date'][6:]}"

    st.markdown(f"""
    <div style="border:1px solid {rc};border-radius:4px;padding:20px 28px;
                margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div style="font-family:'DM Mono';font-size:11px;color:{MUTED};
                        letter-spacing:.1em;text-transform:uppercase;">
                vs {last_ff['rival_name']} · {fecha}
            </div>
            <div style="font-family:'Syne',sans-serif;font-size:42px;font-weight:800;
                        color:{TEXT};line-height:1.1;margin-top:4px;">
                {int(last_ff['score_bilbao'])}
                <span style="color:{MUTED};font-size:28px;">—</span>
                {int(last_ff['score_rival'])}
            </div>
        </div>
        <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:{rc};">
            {result_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Net Rating", f"{last_nr['nrtg']:+.1f}",
                  help="Diferencia ataque-defensa por 100 posesiones")
    with c2:
        st.metric("ORtg", f"{last_nr['ortg']:.1f}",
                  help="Puntos anotados por cada 100 posesiones")
    with c3:
        st.metric("DRtg", f"{last_nr['drtg']:.1f}",
                  help="Puntos encajados por cada 100 posesiones")
    with c4:
        st.metric("eFG%", f"{last_ff['efg_pct']*100:.1f}%",
                  help="Eficiencia de tiro ajustada (triples valen más)")
    with c5:
        st.metric("TOV%", f"{last_ff['tov_pct']*100:.1f}%",
                  help="% de posesiones que terminan en pérdida. Más bajo = mejor.")

    st.markdown("<br>", unsafe_allow_html=True)

    engine = get_engine(os.getenv("DATABASE_URL", "sqlite:///./data/db/bilbao.db"))

    tab1, tab2, tab3 = st.tabs(["BOXSCORE", "FOUR FACTORS", "PARCIALES POR CUARTO"])

    # ── Boxscore ──────────────────────────────────────────────────────────────
    with tab1:
        insight_box(
            "Estadísticas individuales de los jugadores de Bilbao en este partido. "
            "<b>T2/T3/TL</b>: tiros anotados/intentados de 2, 3 y tiro libre. "
            "<b>RO/RD</b>: rebotes ofensivos y defensivos. "
            "<b>Rob</b>: robos. <b>Tap</b>: tapones. <b>Perd</b>: pérdidas. "
            "Los jugadores con 15+ puntos aparecen resaltados."
        )
        boxscore_ok = False
        try:
            last_match_id = _get_last_match_id(engine)
            if last_match_id:
                bs_real = boxscore_bilbao(engine, match_id=last_match_id)
                if not bs_real.empty:
                    bs = bs_real[["player_name","pts","fg2m","fg2a","fg3m","fg3a",
                                  "ftm","fta","ast","orb","drb","stl","tov","blk","pf"]].copy()
                    bs.columns = ["Jugador","Pts","T2M","T2A","T3M","T3A",
                                  "TLM","TLA","Ast","RO","RD","Rob","Perd","Tap","Falt"]
                    bs = bs.sort_values("Pts", ascending=False)

                    def _hi(val):
                        if isinstance(val, (int, float)) and val >= 15:
                            return f"color:{ACCENT};font-weight:500"
                        return ""

                    st.dataframe(bs.style.applymap(_hi, subset=["Pts"]),
                                 use_container_width=True, hide_index=True)
                    buf = io.StringIO()
                    bs.to_csv(buf, index=False)
                    st.download_button("⬇  Boxscore (CSV)", buf.getvalue(),
                                       "bilbao_last_match_boxscore.csv", "text/csv")
                    boxscore_ok = True
        except Exception:
            pass

        if not boxscore_ok:
            st.info("Boxscore no disponible. Comprueba que el partido está cargado en BD.")

    # ── Four Factors ──────────────────────────────────────────────────────────
    with tab2:
        insight_box(
            "Comparación de los cuatro factores de este partido respecto a la media de temporada. "
            "La flecha verde indica que estuvimos por encima de nuestra media habitual; "
            "la roja, por debajo. En <b>TOV%</b> la flecha verde significa que perdimos menos "
            "balones de lo habitual (lo cual es bueno)."
        )

        factors = [
            ("efg_pct", "eFG%",    "Eficiencia de tiro",                   True),
            ("tov_pct", "TOV%",    "% pérdidas — más bajo es mejor",       False),
            ("orb_pct", "ORB%",    "Rebotes ofensivos capturados",         True),
            ("ft_rate", "FT Rate", "Agresividad yendo a la línea de TL",   True),
        ]
        cols = st.columns(4)
        for i, (col_name, label, desc, higher_better) in enumerate(factors):
            val   = last_ff[col_name]
            avg   = ff[col_name].mean()
            delta = val - avg
            better = (delta >= 0 and higher_better) or (delta < 0 and not higher_better)
            with cols[i]:
                st.metric(label, f"{val*100:.1f}%",
                          delta=f"{delta*100:+.1f}pp vs media",
                          delta_color="normal" if better else "inverse",
                          help=desc)

        st.markdown("<br>", unsafe_allow_html=True)
        _radar_match_vs_season(last_ff, ff)

    # ── Parciales ─────────────────────────────────────────────────────────────
    with tab3:
        insight_box(
            "Puntos anotados por Bilbao (amarillo) y el rival (gris) en cada cuarto. "
            "Un cuarto donde la barra amarilla es más alta indica que Bilbao dominó ese periodo. "
            "Útil para identificar en qué momentos del partido se gana o se pierde el partido."
        )
        _quarter_breakdown(last_ff, engine)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_last_match_id(engine):
    from sqlalchemy import text
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id FROM matches ORDER BY date DESC LIMIT 1")).fetchone()
    return r[0] if r else None


def _get_bilbao_role(engine, match_id):
    from sqlalchemy import text
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT bilbao_role FROM matches WHERE id = :mid"), {"mid": match_id}
        ).fetchone()
    return r[0] if r else "home"


def _radar_match_vs_season(last_ff, ff):
    factors = ["efg_pct", "orb_pct", "ft_rate"]
    labels  = ["eFG%", "ORB%", "FT Rate"]
    season  = [ff[f].mean() * 100 for f in factors]
    this    = [last_ff[f] * 100 for f in factors]
    rc      = WIN_CLR if last_ff["result"] == "W" else LOSS_CLR

    fig = go.Figure()
    for vals, color, name in [
        (season + [season[0]], MUTED,  "Media temporada"),
        (this   + [this[0]],   rc,     "Este partido"),
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
        height=320, margin=dict(l=48, r=48, t=24, b=48),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def _quarter_breakdown(last_ff, engine):
    from sqlalchemy import text
    try:
        last_match_id = _get_last_match_id(engine)
        if not last_match_id:
            st.info("No se encontró el partido en BD.")
            return

        bilbao_role = _get_bilbao_role(engine, last_match_id)
        df = pd.read_sql(
            text("""
                SELECT quarter,
                    MIN(score_home) as sh_start, MAX(score_home) as sh_end,
                    MIN(score_away) as sa_start, MAX(score_away) as sa_end
                FROM events
                WHERE match_id = :mid AND score_home IS NOT NULL
                GROUP BY quarter ORDER BY quarter
            """),
            engine, params={"mid": last_match_id},
        )

        if df.empty:
            st.info("Sin datos de parciales.")
            return

        df["bilbao_q"] = df.apply(lambda r:
            r["sh_end"] - r["sh_start"] if bilbao_role == "home"
            else r["sa_end"] - r["sa_start"], axis=1)
        df["rival_q"] = df.apply(lambda r:
            r["sa_end"] - r["sa_start"] if bilbao_role == "home"
            else r["sh_end"] - r["sh_start"], axis=1)

        quarters = [f"Q{int(q)}" for q in df["quarter"]]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=quarters, y=df["bilbao_q"],
                             name="Bilbao", marker_color=ACCENT, marker_line_width=0))
        fig.add_trace(go.Bar(x=quarters, y=df["rival_q"],
                             name="Rival", marker_color="#444", marker_line_width=0))
        layout = base_layout("Puntos anotados por cuarto", height=340, has_legend=True)
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

        tbl = pd.DataFrame({
            "Cuarto":  quarters,
            "Bilbao":  df["bilbao_q"].values,
            "Rival":   df["rival_q"].values,
            "Diferencia": (df["bilbao_q"] - df["rival_q"]).values,
        })
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    except Exception as e:
        st.warning(f"No se pudo cargar el desglose por cuartos: {e}")
