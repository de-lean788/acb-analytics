"""
Tests básicos del pipeline de ingesta.
Ejecutar con: pytest tests/ -v
"""

import pytest
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Base, Match, Event, Player, create_tables
from pipeline.ingest import parse_filename, validate_csv, load_match, BILBAO_KEYWORD


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """BD en memoria para tests."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def sample_df():
    """DataFrame mínimo válido para tests."""
    rows = []
    # Quinteto inicial (home = Bilbao)
    for i, name in enumerate(["Player A", "Player B", "Player C", "Player D", "Player E"]):
        rows.append({
            "match_id": 99999, "quarter": 1, "minute": 10, "second": 0,
            "time_str": "Q1 10:00", "order": 10 + i,
            "is_local": True, "team_role": "home",
            "score_home": 0, "score_away": 0,
            "play_type": 599, "play_type_desc": "Quinteto inicial",
            "play_tag": None, "player_name": name,
            "player_id": float(1000 + i), "player_number": float(i + 1),
            **{col: 0.0 for col in [
                "pts","ft_made","ft_att","fg2_made","fg2_att",
                "fg3_made","fg3_att","assists","off_reb","def_reb",
                "tot_reb","steals","turnovers","blocks","fouls","fouls_drawn",
            ]},
        })
    # Quinteto inicial (away = rival)
    for i, name in enumerate(["Rival A", "Rival B", "Rival C", "Rival D", "Rival E"]):
        rows.append({**rows[0], "team_role": "away", "is_local": False,
                     "player_name": name, "player_id": float(2000 + i),
                     "order": 20 + i})
    # Un evento de tiro
    rows.append({
        "match_id": 99999, "quarter": 1, "minute": 9, "second": 30,
        "time_str": "Q1 09:30", "order": 100,
        "is_local": True, "team_role": "home",
        "score_home": 2, "score_away": 0,
        "play_type": 1, "play_type_desc": "2 puntos anotado (local)",
        "play_tag": None, "player_name": "Player A",
        "player_id": 1000.0, "player_number": 1.0,
        "pts": 2.0, "ft_made": 0.0, "ft_att": 0.0,
        "fg2_made": 1.0, "fg2_att": 1.0, "fg3_made": 0.0, "fg3_att": 0.0,
        "assists": 0.0, "off_reb": 0.0, "def_reb": 0.0, "tot_reb": 0.0,
        "steals": 0.0, "turnovers": 0.0, "blocks": 0.0, "fouls": 0.0, "fouls_drawn": 0.0,
    })
    return pd.DataFrame(rows)


# ── Tests parse_filename ──────────────────────────────────────────────────────

def test_parse_filename_bilbao_home():
    path = Path("20251026_104492_SurneBilbaoBasket_vs_MoraBancAndorra_plays.csv")
    meta = parse_filename(path)
    assert meta["match_id"] == 104492
    assert meta["date"] == "20251026"
    assert meta["bilbao_role"] == "home"
    assert meta["home_team"] == "SurneBilbaoBasket"


def test_parse_filename_bilbao_away():
    path = Path("20251019_104481_JoventutBadalona_vs_SurneBilbaoBasket_plays.csv")
    meta = parse_filename(path)
    assert meta["match_id"] == 104481
    assert meta["bilbao_role"] == "away"
    assert meta["away_team"] == "SurneBilbaoBasket"


def test_parse_filename_invalid():
    with pytest.raises(ValueError):
        parse_filename(Path("fichero_mal_formado.csv"))


# ── Tests validate_csv ────────────────────────────────────────────────────────

def test_validate_csv_ok(sample_df):
    warnings = validate_csv(sample_df, "test.csv")
    # No debería haber warnings críticos en un DF válido
    assert isinstance(warnings, list)


def test_validate_csv_missing_column(sample_df):
    df_bad = sample_df.drop(columns=["quarter"])
    with pytest.raises(ValueError, match="columnas requeridas ausentes"):
        validate_csv(df_bad, "test.csv")


# ── Tests load_match ──────────────────────────────────────────────────────────

def test_load_match_creates_records(tmp_path, engine, sample_df):
    csv_path = tmp_path / "20251026_99999_SurneBilbaoBasket_vs_TestRival_plays.csv"
    sample_df.to_csv(csv_path, index=False)

    with Session(engine) as session:
        ok, warnings = load_match(csv_path, session)
        session.commit()

    assert ok is True

    with Session(engine) as session:
        match = session.get(Match, 99999)
        assert match is not None
        assert match.bilbao_role == "home"
        assert match.home_team == "SurneBilbaoBasket"

        events = session.query(Event).filter_by(match_id=99999).all()
        assert len(events) == len(sample_df)

        players = session.query(Player).all()
        assert len(players) >= 5  # al menos el quinteto de Bilbao


def test_load_match_idempotent(tmp_path, engine, sample_df):
    """Cargar el mismo partido dos veces no debe duplicar registros."""
    csv_path = tmp_path / "20251026_99999_SurneBilbaoBasket_vs_TestRival_plays.csv"
    sample_df.to_csv(csv_path, index=False)

    with Session(engine) as session:
        load_match(csv_path, session)
        session.commit()

    with Session(engine) as session:
        ok2, warnings = load_match(csv_path, session)
        session.commit()

    assert ok2 is False  # segundo load debe ser saltado

    with Session(engine) as session:
        count = session.query(Match).filter_by(id=99999).count()
        assert count == 1  # solo un partido


def test_is_bilbao_flag(tmp_path, engine, sample_df):
    """El campo is_bilbao debe ser True para eventos del equipo local (home=Bilbao)."""
    csv_path = tmp_path / "20251026_99999_SurneBilbaoBasket_vs_TestRival_plays.csv"
    sample_df.to_csv(csv_path, index=False)

    with Session(engine) as session:
        load_match(csv_path, session)
        session.commit()

    with Session(engine) as session:
        bilbao_events = session.query(Event).filter_by(match_id=99999, is_bilbao=True).count()
        rival_events = session.query(Event).filter_by(match_id=99999, is_bilbao=False).count()
        assert bilbao_events > 0
        assert rival_events > 0
