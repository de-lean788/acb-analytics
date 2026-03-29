"""
Fixtures compartidos entre tests.
Crea una BD en memoria con datos mínimos pero realistas.
"""

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db.models import Base, Match, Event, Player


BILBAO_PLAYERS = [
    {"id": 1001.0, "name": "Melwin Pantzar",    "number": 1.0},
    {"id": 1002.0, "name": "Darrun Hilliard",   "number": 2.0},
    {"id": 1003.0, "name": "Tryggvi Hlinason",  "number": 3.0},
    {"id": 1004.0, "name": "Justin Jaworski",   "number": 4.0},
    {"id": 1005.0, "name": "Martin Krampelj",   "number": 5.0},
]

RIVAL_PLAYERS = [
    {"id": 2001.0, "name": "Rival A", "number": 11.0},
    {"id": 2002.0, "name": "Rival B", "number": 12.0},
    {"id": 2003.0, "name": "Rival C", "number": 13.0},
    {"id": 2004.0, "name": "Rival D", "number": 14.0},
    {"id": 2005.0, "name": "Rival E", "number": 15.0},
]

_ZERO_STATS = {k: 0.0 for k in [
    "pts","fg2_made","fg2_att","fg3_made","fg3_att","ft_made","ft_att",
    "assists","off_reb","def_reb","tot_reb","steals","turnovers","blocks","fouls","fouls_drawn",
]}
_NULL_STATS = {k: None for k in _ZERO_STATS}


def _make_player_events(match_id, is_bilbao, players, stats_list, score_home=80, score_away=75):
    """
    Genera eventos mínimos para boxscore (MAX stats) y reconstrucción de lineups
    (Quinteto inicial + Fin de cuarto).
    """
    team_role = "home" if is_bilbao else "away"
    events = []

    # Quinteto inicial (order 10..14)
    for i, player in enumerate(players):
        events.append(Event(
            match_id=match_id,
            quarter=1, minute=10, second=0,
            time_str="Q1 10:00", order=10 + i,
            is_local=is_bilbao, team_role=team_role, is_bilbao=is_bilbao,
            score_home=0, score_away=0,
            play_type=599, play_type_desc="Quinteto inicial",
            player_id=player["id"], player_name=player["name"], player_number=player["number"],
            **_ZERO_STATS,
        ))

    # Stats acumulados finales (order 9000..9004)
    for i, (player, stats) in enumerate(zip(players, stats_list)):
        events.append(Event(
            match_id=match_id,
            quarter=4, minute=0, second=5,
            time_str="Q4 00:05", order=9000 + i,
            is_local=is_bilbao, team_role=team_role, is_bilbao=is_bilbao,
            score_home=score_home, score_away=score_away,
            play_type=1, play_type_desc="2 puntos anotado (local)",
            player_id=player["id"], player_name=player["name"], player_number=player["number"],
            **stats,
        ))

    # Fin de cuarto (order 9999) — cierra el stint
    events.append(Event(
        match_id=match_id,
        quarter=4, minute=0, second=0,
        time_str="Q4 00:00", order=9999,
        is_local=is_bilbao, team_role=team_role, is_bilbao=is_bilbao,
        score_home=score_home, score_away=score_away,
        play_type=122, play_type_desc="Fin de cuarto",
        player_id=None, player_name=None, player_number=None,
        **_NULL_STATS,
    ))

    return events


def make_engine_with_data():
    """
    BD SQLite en memoria con 2 partidos:
      - match 1: Bilbao local (home), victoria 85-75
      - match 2: Bilbao visitante (away), derrota 70-80
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as s:
        for p in BILBAO_PLAYERS + RIVAL_PLAYERS:
            s.add(Player(id=p["id"], name=p["name"], number=p["number"]))

        # ── Partido 1: Bilbao home, gana 85-75 ────────────────────────────────
        s.add(Match(
            id=1, date="20251019",
            home_team="SurneBilbao", away_team="Rival1",
            bilbao_role="home",
            score_home_final=85, score_away_final=75,
            source_file="test1.csv",
        ))

        bilbao_stats_1 = [
            dict(pts=18, fg2_made=4, fg2_att=7, fg3_made=2, fg3_att=5, ft_made=4, ft_att=5,
                 assists=3, off_reb=1, def_reb=4, tot_reb=5, steals=2, turnovers=1, blocks=0, fouls=2, fouls_drawn=4),
            dict(pts=16, fg2_made=6, fg2_att=9, fg3_made=0, fg3_att=2, ft_made=4, ft_att=6,
                 assists=1, off_reb=2, def_reb=3, tot_reb=5, steals=1, turnovers=2, blocks=1, fouls=3, fouls_drawn=5),
            dict(pts=14, fg2_made=5, fg2_att=8, fg3_made=0, fg3_att=0, ft_made=4, ft_att=6,
                 assists=0, off_reb=3, def_reb=5, tot_reb=8, steals=0, turnovers=1, blocks=2, fouls=2, fouls_drawn=4),
            dict(pts=12, fg2_made=2, fg2_att=4, fg3_made=2, fg3_att=5, ft_made=2, ft_att=2,
                 assists=5, off_reb=0, def_reb=2, tot_reb=2, steals=2, turnovers=2, blocks=0, fouls=1, fouls_drawn=2),
            dict(pts=10, fg2_made=2, fg2_att=5, fg3_made=1, fg3_att=3, ft_made=3, ft_att=4,
                 assists=2, off_reb=1, def_reb=3, tot_reb=4, steals=1, turnovers=1, blocks=0, fouls=3, fouls_drawn=3),
        ]
        rival_stats_1 = [
            dict(pts=15, fg2_made=5, fg2_att=9, fg3_made=1, fg3_att=3, ft_made=2, ft_att=3,
                 assists=2, off_reb=1, def_reb=3, tot_reb=4, steals=1, turnovers=2, blocks=0, fouls=2, fouls_drawn=2),
            dict(pts=14, fg2_made=4, fg2_att=8, fg3_made=2, fg3_att=4, ft_made=0, ft_att=0,
                 assists=3, off_reb=0, def_reb=4, tot_reb=4, steals=2, turnovers=1, blocks=1, fouls=2, fouls_drawn=0),
            dict(pts=13, fg2_made=5, fg2_att=7, fg3_made=0, fg3_att=2, ft_made=3, ft_att=4,
                 assists=1, off_reb=2, def_reb=3, tot_reb=5, steals=0, turnovers=3, blocks=1, fouls=3, fouls_drawn=3),
            dict(pts=10, fg2_made=2, fg2_att=5, fg3_made=2, fg3_att=4, ft_made=0, ft_att=1,
                 assists=4, off_reb=0, def_reb=2, tot_reb=2, steals=1, turnovers=2, blocks=0, fouls=1, fouls_drawn=0),
            dict(pts=13, fg2_made=4, fg2_att=7, fg3_made=1, fg3_att=3, ft_made=2, ft_att=3,
                 assists=2, off_reb=1, def_reb=4, tot_reb=5, steals=2, turnovers=1, blocks=0, fouls=2, fouls_drawn=2),
        ]

        for ev in _make_player_events(1, True, BILBAO_PLAYERS, bilbao_stats_1, 85, 75):
            s.add(ev)
        for ev in _make_player_events(1, False, RIVAL_PLAYERS, rival_stats_1, 85, 75):
            s.add(ev)

        # ── Partido 2: Bilbao away, pierde 70-80 ──────────────────────────────
        s.add(Match(
            id=2, date="20251026",
            home_team="Rival2", away_team="SurneBilbao",
            bilbao_role="away",
            score_home_final=80, score_away_final=70,
            source_file="test2.csv",
        ))

        bilbao_stats_2 = [
            dict(pts=14, fg2_made=4, fg2_att=8, fg3_made=2, fg3_att=5, ft_made=0, ft_att=1,
                 assists=4, off_reb=1, def_reb=3, tot_reb=4, steals=1, turnovers=3, blocks=0, fouls=2, fouls_drawn=1),
            dict(pts=13, fg2_made=5, fg2_att=9, fg3_made=0, fg3_att=1, ft_made=3, ft_att=4,
                 assists=0, off_reb=2, def_reb=5, tot_reb=7, steals=0, turnovers=1, blocks=2, fouls=3, fouls_drawn=4),
            dict(pts=12, fg2_made=4, fg2_att=7, fg3_made=0, fg3_att=0, ft_made=4, ft_att=5,
                 assists=1, off_reb=3, def_reb=4, tot_reb=7, steals=1, turnovers=2, blocks=1, fouls=2, fouls_drawn=4),
            dict(pts=10, fg2_made=1, fg2_att=4, fg3_made=2, fg3_att=6, ft_made=2, ft_att=2,
                 assists=3, off_reb=0, def_reb=2, tot_reb=2, steals=2, turnovers=2, blocks=0, fouls=1, fouls_drawn=2),
            dict(pts=8, fg2_made=2, fg2_att=5, fg3_made=1, fg3_att=2, ft_made=1, ft_att=2,
                 assists=2, off_reb=1, def_reb=2, tot_reb=3, steals=1, turnovers=2, blocks=0, fouls=2, fouls_drawn=1),
        ]
        rival_stats_2 = [
            dict(pts=18, fg2_made=6, fg2_att=9, fg3_made=2, fg3_att=4, ft_made=2, ft_att=3,
                 assists=3, off_reb=1, def_reb=4, tot_reb=5, steals=2, turnovers=1, blocks=0, fouls=2, fouls_drawn=2),
            dict(pts=16, fg2_made=5, fg2_att=8, fg3_made=2, fg3_att=5, ft_made=2, ft_att=2,
                 assists=2, off_reb=0, def_reb=3, tot_reb=3, steals=1, turnovers=2, blocks=1, fouls=2, fouls_drawn=2),
            dict(pts=15, fg2_made=6, fg2_att=8, fg3_made=0, fg3_att=2, ft_made=3, ft_att=4,
                 assists=1, off_reb=2, def_reb=4, tot_reb=6, steals=0, turnovers=2, blocks=2, fouls=3, fouls_drawn=3),
            dict(pts=14, fg2_made=3, fg2_att=6, fg3_made=2, fg3_att=4, ft_made=2, ft_att=3,
                 assists=5, off_reb=0, def_reb=2, tot_reb=2, steals=2, turnovers=1, blocks=0, fouls=1, fouls_drawn=2),
            dict(pts=10, fg2_made=3, fg2_att=6, fg3_made=1, fg3_att=3, ft_made=1, ft_att=2,
                 assists=2, off_reb=1, def_reb=3, tot_reb=4, steals=1, turnovers=2, blocks=0, fouls=2, fouls_drawn=1),
        ]

        for ev in _make_player_events(2, False, BILBAO_PLAYERS, bilbao_stats_2, 80, 70):
            s.add(ev)
        for ev in _make_player_events(2, False, RIVAL_PLAYERS, rival_stats_2, 80, 70):
            s.add(ev)

        s.commit()

    return engine
