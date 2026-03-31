"""
Migración SQLite → Supabase (PostgreSQL)
==========================================
Usa pandas + SQL directo para evitar problemas de compatibilidad de tipos.

Uso:
    python scripts/migrate_to_supabase.py --target "postgresql://..."
"""

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import create_engine, text
from decimal import Decimal


BOOL_COLS = {
    "events":  ["is_local", "is_bilbao"],
    "lineups": ["is_bilbao"],
}

def fix_bools(df, table: str):
    """SQLite guarda booleanos como 0/1 — PostgreSQL necesita True/False."""
    for col in BOOL_COLS.get(table, []):
        if col in df.columns:
            df[col] = df[col].astype(bool)
    return df


def get_pg_engine(url: str):
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif not url.startswith("postgresql"):
        url = "postgresql+psycopg2://" + url.split("://", 1)[1]
    
    return create_engine(
        url, echo=False,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
    )


def get_sqlite_engine(url: str):
    return create_engine(url, echo=False)


CREATE_TABLES_SQL = """
DROP TABLE IF EXISTS lineups CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS players CASCADE;
DROP TABLE IF EXISTS matches CASCADE;

CREATE TABLE matches (
    id          INTEGER PRIMARY KEY,
    date        VARCHAR,
    home_team        VARCHAR,
    away_team        VARCHAR,
    bilbao_role      VARCHAR,
    score_home_final INTEGER,
    score_away_final INTEGER,
    round_number     INTEGER,
    source_file VARCHAR
);

CREATE TABLE players (
    id     DOUBLE PRECISION PRIMARY KEY,
    name   VARCHAR NOT NULL,
    number DOUBLE PRECISION
);

CREATE TABLE events (
    id             SERIAL PRIMARY KEY,
    match_id       INTEGER REFERENCES matches(id),
    quarter        INTEGER NOT NULL,
    minute         INTEGER NOT NULL,
    second         INTEGER NOT NULL,
    time_str       VARCHAR,
    "order"        INTEGER NOT NULL,
    is_local       BOOLEAN NOT NULL,
    team_role      VARCHAR NOT NULL,
    is_bilbao      BOOLEAN NOT NULL,
    score_home     INTEGER,
    score_away     INTEGER,
    play_type      INTEGER,
    play_type_desc VARCHAR,
    play_tag       DOUBLE PRECISION,
    player_id      DOUBLE PRECISION,
    player_name    VARCHAR,
    player_number  DOUBLE PRECISION,
    pts            DOUBLE PRECISION,
    ft_made        DOUBLE PRECISION,
    ft_att         DOUBLE PRECISION,
    fg2_made       DOUBLE PRECISION,
    fg2_att        DOUBLE PRECISION,
    fg3_made       DOUBLE PRECISION,
    fg3_att        DOUBLE PRECISION,
    assists        DOUBLE PRECISION,
    off_reb        DOUBLE PRECISION,
    def_reb        DOUBLE PRECISION,
    tot_reb        DOUBLE PRECISION,
    steals         DOUBLE PRECISION,
    turnovers      DOUBLE PRECISION,
    blocks         DOUBLE PRECISION,
    fouls          DOUBLE PRECISION,
    fouls_drawn    DOUBLE PRECISION
);

CREATE TABLE lineups (
    id                  SERIAL PRIMARY KEY,
    match_id            INTEGER REFERENCES matches(id),
    team_role           VARCHAR NOT NULL,
    is_bilbao           BOOLEAN NOT NULL,
    p1_id               DOUBLE PRECISION,
    p2_id               DOUBLE PRECISION,
    p3_id               DOUBLE PRECISION,
    p4_id               DOUBLE PRECISION,
    p5_id               DOUBLE PRECISION,
    lineup_key          VARCHAR NOT NULL,
    start_quarter       INTEGER NOT NULL,
    start_order         INTEGER NOT NULL,
    end_quarter         INTEGER,
    end_order           INTEGER,
    score_bilbao_start  INTEGER,
    score_rival_start   INTEGER,
    score_bilbao_end    INTEGER,
    score_rival_end     INTEGER
);

CREATE INDEX ix_events_match_order  ON events(match_id, "order");
CREATE INDEX ix_events_player       ON events(player_id);
CREATE INDEX ix_events_play_type    ON events(play_type_desc);
CREATE INDEX ix_lineups_match_team  ON lineups(match_id, team_role);
CREATE INDEX ix_lineups_key         ON lineups(lineup_key);
"""


def migrate(source_url: str, target_url: str, batch_size: int = 1000):
    print(f"\nOrigen : {source_url}")
    print(f"Destino: {target_url[:50]}...\n")

    src = get_sqlite_engine(source_url)
    tgt = get_pg_engine(target_url)

    # ── 1. Crear tablas en PostgreSQL ─────────────────────────────────────────
    print("Creando tablas en Supabase...")
    with tgt.begin() as conn:
        for statement in CREATE_TABLES_SQL.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    print("  Tablas creadas ✓\n")

    # ── 2. Matches ────────────────────────────────────────────────────────────
    matches = pd.read_sql("SELECT * FROM matches", src)
    print(f"Migrando {len(matches)} partidos...", end=" ", flush=True)
    matches.to_sql("matches", tgt, if_exists="append", index=False, chunksize=100)
    print("✓")

    # ── 3. Players ────────────────────────────────────────────────────────────
    players = pd.read_sql("SELECT * FROM players", src)
    print(f"Migrando {len(players)} jugadores...", end=" ", flush=True)
    players.to_sql("players", tgt, if_exists="append", index=False, chunksize=100)
    print("✓")

    # ── 4. Events (en batches) ────────────────────────────────────────────────
    total = pd.read_sql("SELECT COUNT(*) as n FROM events", src).iloc[0, 0]
    print(f"Migrando {total} eventos en batches de {batch_size}...")

    offset = 0
    while True:
        batch = pd.read_sql(
            f'SELECT * FROM events ORDER BY id LIMIT {batch_size} OFFSET {offset}',
            src
        )
        if batch.empty:
            break
        # Quitar la columna id para que PostgreSQL use su SERIAL
        batch = batch.drop(columns=["id"], errors="ignore")
        batch = fix_bools(batch, "events")
        batch.to_sql("events", tgt, if_exists="append", index=False, chunksize=100)
        offset += batch_size
        pct = min(100, int(offset / total * 100))
        print(f"  {pct}%  ({min(offset, total)}/{total})")

    print("  Eventos ✓")

    # ── 5. Lineups ────────────────────────────────────────────────────────────
    lineups = pd.read_sql("SELECT * FROM lineups", src)
    print(f"Migrando {len(lineups)} stints de lineups...", end=" ", flush=True)
    lineups = lineups.drop(columns=["id"], errors="ignore")
    lineups = fix_bools(lineups, "lineups")
    lineups.to_sql("lineups", tgt, if_exists="append", index=False, chunksize=100)
    print("✓")

    # ── 6. Verificación ───────────────────────────────────────────────────────
    print("\nVerificando...")
    with tgt.connect() as conn:
        for table in ["matches", "players", "events", "lineups"]:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table:10}: {n} filas")

    print("\n✅ Migración completada.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migración SQLite → Supabase")
    parser.add_argument(
        "--source",
        default="sqlite:///./data/db/bilbao.db",
        help="URL BD origen (default: SQLite local)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="URL BD destino (Supabase connection string)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Tamaño de batch para eventos (default: 1000)",
    )
    args = parser.parse_args()
    migrate(args.source, args.target, args.batch_size)
