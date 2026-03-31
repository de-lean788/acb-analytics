"""
Pipeline de ingesta — Fase 1
==============================
Lee todos los CSVs del directorio data/csv/, los valida,
y los carga en SQLite manteniendo idempotencia (no duplica si relanzas).

Uso:
    python -m pipeline.ingest                          # ingesta todos los CSVs
    python -m pipeline.ingest --file data/csv/XX.csv  # ingesta un fichero específico
    python -m pipeline.ingest --reset                  # borra la BD y recarga todo
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Base, Event, Match, Player, get_engine, create_tables

# ── Constantes ────────────────────────────────────────────────────────────────

BILBAO_KEYWORD = os.getenv("BILBAO_TEAM_KEYWORD", "SurneBilbao")

# ── Calendario: match_id → número de jornada ─────────────────────────────────

def _load_round_map() -> dict[int, int]:
    """Carga acb_calendar_2526.json y devuelve {match_id: round_number}."""
    cal_path = Path(__file__).parent.parent / "data" / "acb_calendar_2526.json"
    if not cal_path.exists():
        return {}
    try:
        with open(cal_path) as f:
            data = json.load(f)
        return {
            e["match_id"]: e["jornada"]
            for e in data.get("jornadas", [])
            if e.get("match_id") and e.get("jornada")
        }
    except Exception:
        return {}

_ROUND_MAP: dict[int, int] = _load_round_map()

# play_type_desc que indican sustitución
SUB_IN = "Entra a pista"
SUB_OUT = "Sustitución"
STARTING_FIVE = "Quinteto inicial"

# Columnas numéricas de stats
STAT_COLS = [
    "pts", "ft_made", "ft_att", "fg2_made", "fg2_att",
    "fg3_made", "fg3_att", "assists", "off_reb", "def_reb",
    "tot_reb", "steals", "turnovers", "blocks", "fouls", "fouls_drawn",
]


# ── Parsing del nombre de fichero ─────────────────────────────────────────────

def parse_filename(path: Path) -> dict:
    """
    Extrae metadatos del nombre del fichero.
    Formato esperado: YYYYMMDD_matchid_HomeTeam_vs_AwayTeam_plays.csv
    """
    name = path.stem  # sin extensión
    pattern = r"^(\d{8})_(\d+)_(.+)_vs_(.+)_plays$"
    m = re.match(pattern, name)
    if not m:
        raise ValueError(f"Nombre de fichero no reconocido: {path.name}")

    date, match_id, home_raw, away_raw = m.groups()
    bilbao_role = "home" if BILBAO_KEYWORD.lower() in home_raw.lower() else "away"

    return {
        "date": date,
        "match_id": int(match_id),
        "home_team": home_raw,
        "away_team": away_raw,
        "bilbao_role": bilbao_role,
    }


# ── Validación del CSV ────────────────────────────────────────────────────────

REQUIRED_COLS = {
    "match_id", "quarter", "minute", "second", "order",
    "is_local", "team_role", "score_home", "score_away",
    "play_type", "play_type_desc", "player_name", "player_id",
}

def validate_csv(df: pd.DataFrame, filename: str) -> list[str]:
    """Devuelve lista de warnings. Si hay errores críticos lanza excepción."""
    warnings = []

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{filename}: columnas requeridas ausentes: {missing}")

    # Sustituciones pareadas
    entries = len(df[df["play_type_desc"] == SUB_IN])
    exits = len(df[df["play_type_desc"] == SUB_OUT])
    if entries != exits:
        warnings.append(f"Sustituciones no pareadas: {entries} entradas vs {exits} salidas")

    # Quinteto inicial presente
    if len(df[df["play_type_desc"] == STARTING_FIVE]) == 0:
        warnings.append("No se encontró quinteto inicial")

    return warnings


# ── Detección del rol de Bilbao dentro del CSV ────────────────────────────────

def detect_bilbao_role(df: pd.DataFrame, bilbao_role_from_filename: str) -> str:
    """
    Confirma que el rol inferido del nombre de fichero coincide con los datos.
    Bilbao siempre aparece en el quinteto inicial: si bilbao_role='home',
    sus jugadores deben tener is_local=True.
    """
    starting = df[df["play_type_desc"] == STARTING_FIVE]
    if starting.empty:
        return bilbao_role_from_filename  # no podemos confirmar, confiamos en el nombre

    home_players = starting[starting["team_role"] == "home"]["player_name"].dropna().tolist()
    away_players = starting[starting["team_role"] == "away"]["player_name"].dropna().tolist()

    # Heurística: el equipo con más jugadores conocidos de Bilbao es el nuestro.
    # Para arrancar confiamos en el nombre del fichero; esta función es para auditoría.
    return bilbao_role_from_filename


# ── Carga de jugadores (upsert) ───────────────────────────────────────────────

def upsert_players(df: pd.DataFrame, session: Session) -> None:
    """Inserta jugadores nuevos; ignora los que ya existen."""
    players_df = (
        df[df["player_id"].notna()][["player_id", "player_name", "player_number"]]
        .drop_duplicates(subset=["player_id"])
    )

    existing_ids = {p.id for p in session.query(Player).all()}

    new_players = []
    for _, row in players_df.iterrows():
        if row["player_id"] not in existing_ids:
            new_players.append(Player(
                id=row["player_id"],
                name=row["player_name"],
                number=row.get("player_number"),
            ))

    if new_players:
        session.bulk_save_objects(new_players)


# ── Carga del partido ─────────────────────────────────────────────────────────

def load_match(path: Path, session: Session, dry_run: bool = False) -> tuple[bool, list[str]]:
    """
    Carga un CSV en la BD. Retorna (cargado: bool, warnings: list[str]).
    Si el partido ya existe, lo salta (idempotente).
    """
    meta = parse_filename(path)
    warnings = []

    # Idempotencia: si ya existe el partido, saltamos
    existing = session.get(Match, meta["match_id"])
    if existing:
        return False, [f"Ya existe match_id={meta['match_id']}, saltando"]

    df = pd.read_csv(path)
    warnings = validate_csv(df, path.name)

    if dry_run:
        return True, warnings

    # Marcador final (último evento con score)
    last_scored = df[df["score_home"].notna()].iloc[-1]

    # Crear partido
    match = Match(
        id=meta["match_id"],
        date=meta["date"],
        home_team=meta["home_team"],
        away_team=meta["away_team"],
        bilbao_role=meta["bilbao_role"],
        score_home_final=int(last_scored["score_home"]),
        score_away_final=int(last_scored["score_away"]),
        source_file=path.name,
        round_number=_ROUND_MAP.get(meta["match_id"]),
    )
    session.add(match)

    # Upsert jugadores
    upsert_players(df, session)

    # Eventos
    bilbao_team_role = meta["bilbao_role"]
    events = []
    for _, row in df.iterrows():
        event = Event(
            match_id=meta["match_id"],
            quarter=int(row["quarter"]),
            minute=int(row["minute"]),
            second=int(row["second"]),
            time_str=row.get("time_str"),
            order=int(row["order"]),
            is_local=bool(row["is_local"]),
            team_role=row["team_role"],
            is_bilbao=(row["team_role"] == bilbao_team_role),
            score_home=int(row["score_home"]) if pd.notna(row["score_home"]) else None,
            score_away=int(row["score_away"]) if pd.notna(row["score_away"]) else None,
            play_type=int(row["play_type"]) if pd.notna(row["play_type"]) else None,
            play_type_desc=row.get("play_type_desc"),
            play_tag=row.get("play_tag"),
            player_id=row["player_id"] if pd.notna(row.get("player_id")) else None,
            player_name=row.get("player_name"),
            player_number=row.get("player_number"),
            **{col: (row[col] if pd.notna(row.get(col)) else None) for col in STAT_COLS},
        )
        events.append(event)

    session.bulk_save_objects(events)
    return True, warnings


# ── Runner principal ──────────────────────────────────────────────────────────

def run_ingestion(csv_dir: Path, specific_file: Path | None = None, reset: bool = False):
    engine = get_engine()

    if reset:
        print("⚠️  Reset: eliminando tablas existentes...")
        Base.metadata.drop_all(engine)

    create_tables(engine)

    files = [specific_file] if specific_file else sorted(csv_dir.glob("*_plays.csv"))
    if not files:
        print(f"No se encontraron CSVs en {csv_dir}")
        return

    print(f"Procesando {len(files)} fichero(s)...\n")

    loaded = skipped = errors = 0

    with Session(engine) as session:
        for path in files:
            try:
                ok, warnings = load_match(path, session)
                if ok:
                    session.commit()
                    status = "✓"
                    loaded += 1
                else:
                    status = "–"
                    skipped += 1

                warn_str = f"  ⚠ {', '.join(warnings)}" if warnings else ""
                print(f"  {status} {path.name}{warn_str}")

            except Exception as e:
                session.rollback()
                print(f"  ✗ {path.name}  ERROR: {e}")
                errors += 1

    print(f"\nResumen: {loaded} cargados | {skipped} saltados | {errors} errores")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestión de CSVs ACB a SQLite")
    parser.add_argument("--dir", type=Path, default=Path("data/csv"),
                        help="Directorio con los CSVs (default: data/csv)")
    parser.add_argument("--file", type=Path, default=None,
                        help="Carga un único fichero CSV")
    parser.add_argument("--reset", action="store_true",
                        help="Elimina la BD y recarga todo desde cero")
    args = parser.parse_args()

    run_ingestion(
        csv_dir=args.dir,
        specific_file=args.file,
        reset=args.reset,
    )
