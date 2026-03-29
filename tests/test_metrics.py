"""
Tests del módulo de métricas.
"""

import pytest
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Base, Match, Event, Player
from analytics.metrics import (
    boxscore_bilbao, team_stats, four_factors,
    shooting_profile, net_ratings, season_summary,
)
from tests.fixtures import make_engine_with_data


# ── Fixture compartido ────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    return make_engine_with_data()


# ── Tests boxscore ────────────────────────────────────────────────────────────

def test_boxscore_returns_only_bilbao(engine):
    df = boxscore_bilbao(engine)
    assert df["is_bilbao"].all()


def test_boxscore_filter_by_match(engine):
    df = boxscore_bilbao(engine, match_id=1)
    assert len(df) > 0
    assert (df["match_id"] == 1).all()


# ── Tests four factors ────────────────────────────────────────────────────────

def test_four_factors_columns(engine):
    ff = four_factors(engine)
    for col in ["efg_pct", "tov_pct", "orb_pct", "ft_rate", "ff_score"]:
        assert col in ff.columns, f"Falta columna: {col}"


def test_four_factors_ranges(engine):
    ff = four_factors(engine)
    assert ff["efg_pct"].between(0, 1).all(), "eFG% fuera de rango [0,1]"
    assert ff["tov_pct"].between(0, 1).all(), "TOV% fuera de rango [0,1]"
    assert ff["orb_pct"].between(0, 1).all(), "ORB% fuera de rango [0,1]"
    assert (ff["ft_rate"] >= 0).all(), "FT Rate negativo"


def test_four_factors_one_row_per_match(engine):
    ff = four_factors(engine)
    ts = team_stats(engine)
    assert len(ff) == len(ts)


# ── Tests net ratings ─────────────────────────────────────────────────────────

def test_net_ratings_columns(engine):
    nr = net_ratings(engine)
    for col in ["ortg", "drtg", "nrtg"]:
        assert col in nr.columns

def test_net_ratings_formula(engine):
    nr = net_ratings(engine)
    # nrtg debe ser exactamente ortg - drtg
    diff = (nr["ortg"] - nr["drtg"] - nr["nrtg"]).abs()
    assert (diff < 0.1).all(), "NRtg != ORtg - DRtg"


def test_net_ratings_positive_ortg(engine):
    nr = net_ratings(engine)
    assert (nr["ortg"] > 0).all(), "ORtg no puede ser negativo"


# ── Tests shooting profile ────────────────────────────────────────────────────

def test_shooting_profile_ts_pct_range(engine):
    sp = shooting_profile(engine, min_games=1)
    # TS% puede superar 1.0 en muestras muy pequeñas con muchos TL, pero no debería
    # ser negativo ni NaN
    assert sp["ts_pct"].notna().all()
    assert (sp["ts_pct"] > 0).all()


def test_shooting_profile_min_games_filter(engine):
    sp_1 = shooting_profile(engine, min_games=1)
    sp_2 = shooting_profile(engine, min_games=2)
    assert len(sp_1) >= len(sp_2)


# ── Tests season summary ──────────────────────────────────────────────────────

def test_season_summary_keys(engine):
    ss = season_summary(engine)
    for key in ["record", "wins", "losses", "avg_ortg", "avg_drtg", "avg_nrtg",
                "four_factors", "net_ratings", "shooting_profile"]:
        assert key in ss, f"Falta key: {key}"


def test_season_summary_wins_losses_consistent(engine):
    ss = season_summary(engine)
    ff = ss["four_factors"]
    assert ss["wins"] + ss["losses"] == len(ff)
