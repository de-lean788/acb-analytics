"""
Modelo de datos — Surne Bilbao Analytics
=========================================
Tablas:
  - matches     : metadatos de cada partido
  - players     : catálogo de jugadores (deduplicado por player_id)
  - events      : play-by-play completo (1 fila = 1 evento)
  - lineups     : quintetos reconstruidos (quién está en pista en cada momento)
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    ForeignKey, UniqueConstraint, Index, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship
import os


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    date = Column(String, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    bilbao_role = Column(String, nullable=False)
    score_home_final = Column(Integer)
    score_away_final = Column(Integer)
    source_file = Column(String, nullable=False)

    events = relationship("Event", back_populates="match", cascade="all, delete-orphan")
    lineups = relationship("Lineup", back_populates="match", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Match {self.date} {self.home_team} vs {self.away_team}>"


class Player(Base):
    __tablename__ = "players"

    id = Column(Float, primary_key=True)
    name = Column(String, nullable=False)
    number = Column(Float)

    __table_args__ = (
        Index("ix_players_name", "name"),
    )

    def __repr__(self):
        return f"<Player #{int(self.number) if self.number else '?'} {self.name}>"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)

    quarter = Column(Integer, nullable=False)
    minute = Column(Integer, nullable=False)
    second = Column(Integer, nullable=False)
    time_str = Column(String)
    order = Column(Integer, nullable=False)

    is_local = Column(Boolean, nullable=False)
    team_role = Column(String, nullable=False)
    is_bilbao = Column(Boolean, nullable=False)

    score_home = Column(Integer)
    score_away = Column(Integer)

    play_type = Column(Integer)
    play_type_desc = Column(String)
    play_tag = Column(Float)

    player_id = Column(Float, nullable=True)
    player_name = Column(String)
    player_number = Column(Float)

    pts = Column(Float)
    ft_made = Column(Float)
    ft_att = Column(Float)
    fg2_made = Column(Float)
    fg2_att = Column(Float)
    fg3_made = Column(Float)
    fg3_att = Column(Float)
    assists = Column(Float)
    off_reb = Column(Float)
    def_reb = Column(Float)
    tot_reb = Column(Float)
    steals = Column(Float)
    turnovers = Column(Float)
    blocks = Column(Float)
    fouls = Column(Float)
    fouls_drawn = Column(Float)

    match = relationship("Match", back_populates="events")

    __table_args__ = (
        Index("ix_events_match_order", "match_id", "order"),
        Index("ix_events_player", "player_id"),
        Index("ix_events_play_type", "play_type_desc"),
    )

    def __repr__(self):
        return f"<Event Q{self.quarter} {self.time_str} {self.play_type_desc} {self.player_name}>"


class Lineup(Base):
    __tablename__ = "lineups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_role = Column(String, nullable=False)
    is_bilbao = Column(Boolean, nullable=False)

    p1_id = Column(Float)
    p2_id = Column(Float)
    p3_id = Column(Float)
    p4_id = Column(Float)
    p5_id = Column(Float)
    lineup_key = Column(String, nullable=False)

    start_quarter = Column(Integer, nullable=False)
    start_order = Column(Integer, nullable=False)
    end_quarter = Column(Integer)
    end_order = Column(Integer)

    score_bilbao_start = Column(Integer)
    score_rival_start = Column(Integer)
    score_bilbao_end = Column(Integer)
    score_rival_end = Column(Integer)

    match = relationship("Match", back_populates="lineups")

    __table_args__ = (
        Index("ix_lineups_match_team", "match_id", "team_role"),
        Index("ix_lineups_key", "lineup_key"),
    )

    def __repr__(self):
        return f"<Lineup {self.lineup_key} Q{self.start_quarter} order={self.start_order}>"


def get_engine(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./data/db/bilbao.db")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)

    if url.startswith("postgresql"):
        return create_engine(
            url, echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"sslmode": "require"},
        )
    else:
        return create_engine(url, echo=False)


def create_tables(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    print(f"Tablas creadas en: {engine.url}")
