"""
Surne Bilbao Analytics — Dashboard
=====================================
Ejecutar con:  streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Surne Bilbao Analytics",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
}
h1, h2, h3 { font-family: 'Syne', sans-serif; letter-spacing: -0.03em; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0a0a0a;
    border-right: 1px solid #1f1f1f;
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
[data-testid="stSidebar"] .stRadio label { 
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    padding: 6px 0;
    border-bottom: 1px solid #1f1f1f;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #111;
    border: 1px solid #222;
    border-radius: 4px;
    padding: 16px;
}
[data-testid="stMetricLabel"] { 
    font-size: 11px !important; 
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #666 !important;
}
[data-testid="stMetricValue"] { 
    font-family: 'Syne', sans-serif;
    font-size: 28px !important;
}

/* DataFrames */
[data-testid="stDataFrame"] { border: 1px solid #1f1f1f; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #1f1f1f; }
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 8px 16px;
    background: transparent;
    border: 1px solid #222;
    border-radius: 2px;
}
.stTabs [aria-selected="true"] {
    background: #e8ff00 !important;
    color: #000 !important;
    border-color: #e8ff00 !important;
}

/* Accent color */
:root { --accent: #e8ff00; }
</style>
""", unsafe_allow_html=True)

from db.models import get_engine

# En Streamlit Cloud, las variables vienen de st.secrets
# En local, vienen del .env — este bloque hace el puente
try:
    import streamlit as _st
    if hasattr(_st, "secrets") and "DATABASE_URL" in _st.secrets:
        import os
        os.environ.setdefault("DATABASE_URL", _st.secrets["DATABASE_URL"])
        os.environ.setdefault("BILBAO_TEAM_KEYWORD",
                              _st.secrets.get("BILBAO_TEAM_KEYWORD", "SurneBilbao"))
except Exception:
    pass
from analytics.metrics import four_factors, net_ratings, shooting_profile, season_summary
from analytics.lineups import rebuild_lineups, on_off_splits, player_impact, lineup_stats

import os

# ── Engine ────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_db_engine():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/db/bilbao.db")
    return get_engine(db_url)

@st.cache_data(ttl=300)
def load_all_data():
    engine = get_db_engine()
    return {
        "ff":  four_factors(engine),
        "nr":  net_ratings(engine),
        "sp":  shooting_profile(engine, min_games=1),
        "pi":  player_impact(engine),
        "ls":  lineup_stats(engine, min_stints=2),
        "ss":  season_summary(engine),
    }

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏀 BILBAO\n### ANALYTICS")
    st.markdown("---")

    vista = st.radio(
        "VISTA",
        ["Impacto de Jugadores", "Tendencia de Temporada",
         "Último Partido", "Análisis de Rival"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if st.button("↺  Actualizar datos", use_container_width=True):
        load_all_data.clear()
        engine = get_db_engine()
        rebuild_lineups(engine)
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Surne Bilbao Basket · 25/26")

# ── Carga de datos ────────────────────────────────────────────────────────────
try:
    data = load_all_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.info("Asegúrate de haber ejecutado `python -m pipeline.ingest --dir data/csv`")
    st.stop()

# ── Router de vistas ──────────────────────────────────────────────────────────
if vista == "Impacto de Jugadores":
    from dashboard.views.player_impact import render
elif vista == "Tendencia de Temporada":
    from dashboard.views.season_trends import render
elif vista == "Último Partido":
    from dashboard.views.last_match import render
else:
    from dashboard.views.rival_analysis import render

render(data)