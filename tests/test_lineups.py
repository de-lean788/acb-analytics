"""
Tests de reconstrucción de lineups y On/Off splits.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.lineups import rebuild_lineups, lineup_stats, on_off_splits, player_impact
from tests.fixtures import make_engine_with_data, BILBAO_PLAYERS


@pytest.fixture
def engine_with_lineups():
    """BD en memoria con datos y lineups reconstruidos."""
    engine = make_engine_with_data()
    rebuild_lineups(engine)
    return engine


# ── rebuild_lineups ───────────────────────────────────────────────────────────

def test_rebuild_lineups_returns_positive_count(engine_with_lineups):
    from sqlalchemy.orm import Session
    from db.models import Lineup
    with Session(engine_with_lineups) as s:
        count = s.query(Lineup).count()
    assert count > 0


def test_rebuild_lineups_idempotent(engine_with_lineups):
    """Llamar dos veces no debe duplicar stints."""
    from sqlalchemy.orm import Session
    from db.models import Lineup

    n1 = rebuild_lineups(engine_with_lineups)
    n2 = rebuild_lineups(engine_with_lineups)
    assert n1 == n2

    with Session(engine_with_lineups) as s:
        count = s.query(Lineup).count()
    assert count == n2


def test_lineup_key_has_5_players(engine_with_lineups):
    from sqlalchemy.orm import Session
    from db.models import Lineup
    with Session(engine_with_lineups) as s:
        lineups = s.query(Lineup).all()
    for l in lineups:
        parts = l.lineup_key.split("-")
        assert len(parts) == 5, f"Lineup key inválida: {l.lineup_key}"


def test_all_lineup_players_are_bilbao(engine_with_lineups):
    """Todos los player_id en los stints de Bilbao deben pertenecer a Bilbao."""
    from sqlalchemy.orm import Session
    from db.models import Lineup
    bilbao_ids = {p["id"] for p in BILBAO_PLAYERS}

    with Session(engine_with_lineups) as s:
        lineups = s.query(Lineup).filter_by(is_bilbao=True).all()

    assert len(lineups) > 0
    for l in lineups:
        for pid in [l.p1_id, l.p2_id, l.p3_id, l.p4_id, l.p5_id]:
            if pid is not None:
                assert pid in bilbao_ids, f"Jugador no-Bilbao en lineup: {pid}"


# ── lineup_stats ──────────────────────────────────────────────────────────────

def test_lineup_stats_columns(engine_with_lineups):
    ls = lineup_stats(engine_with_lineups, min_stints=1)
    for col in ["lineup_key", "stints", "net_pts", "net_per_stint"]:
        assert col in ls.columns


def test_lineup_stats_sorted_by_net_pts(engine_with_lineups):
    ls = lineup_stats(engine_with_lineups, min_stints=1)
    if len(ls) > 1:
        assert ls["net_pts"].iloc[0] >= ls["net_pts"].iloc[-1]


# ── on_off_splits ─────────────────────────────────────────────────────────────

def test_on_off_splits_all_bilbao_players(engine_with_lineups):
    oo = on_off_splits(engine_with_lineups)
    bilbao_names = {p["name"] for p in BILBAO_PLAYERS}
    # Todos los jugadores de Bilbao deben aparecer en el On/Off
    result_names = set(oo["player_name"].tolist())
    assert bilbao_names.issubset(result_names)


def test_on_off_splits_stints_add_up(engine_with_lineups):
    """stints_on + stints_off debe ser constante para todos los jugadores."""
    from sqlalchemy.orm import Session
    from db.models import Lineup
    with Session(engine_with_lineups) as s:
        total_stints = s.query(Lineup).count()

    oo = on_off_splits(engine_with_lineups)
    for _, row in oo.iterrows():
        assert row["stints_on"] + row["stints_off"] == total_stints, \
            f"{row['player_name']}: {row['stints_on']} + {row['stints_off']} != {total_stints}"


def test_on_off_diff_formula(engine_with_lineups):
    """on_off_diff debe ser net_pts_on - net_pts_off."""
    oo = on_off_splits(engine_with_lineups)
    for _, row in oo.iterrows():
        if row["net_pts_off"] is not None:
            expected = row["net_pts_on"] - row["net_pts_off"]
            assert row["on_off_diff"] == expected


# ── player_impact ─────────────────────────────────────────────────────────────

def test_player_impact_sorted_by_on_off_diff(engine_with_lineups):
    pi = player_impact(engine_with_lineups)
    if len(pi) > 1:
        diffs = pi["on_off_diff"].dropna().tolist()
        assert diffs == sorted(diffs, reverse=True)


def test_player_impact_has_shooting_cols(engine_with_lineups):
    pi = player_impact(engine_with_lineups)
    for col in ["pts_per_game", "efg_pct", "ts_pct"]:
        assert col in pi.columns
