"""
Lineups y On/Off splits — Fase 3
==================================
Reconstruye qué 5 jugadores de Bilbao están en pista en cada momento,
calcula stints (intervalos continuos del mismo quinteto) y deriva métricas
On/Off por jugador.

Funciones públicas:
  - rebuild_lineups(engine)     : reconstruye y persiste todos los stints en DB
  - lineup_stats(engine)        : Net Rating y stats por quinteto (acumulado)
  - on_off_splits(engine)       : On/Off Net Rating por jugador
  - player_impact(engine)       : tabla resumen de impacto por jugador
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from analytics.validators import is_bilbao_home
from db.models import Lineup


# ── Constantes ────────────────────────────────────────────────────────────────

SUB_IN  = "Entra a pista"
SUB_OUT = "Sustitución"
STARTING_FIVE = "Quinteto inicial"
QUARTER_END   = "Fin de cuarto"
MATCH_END     = "Fin del partido"
QUARTER_START = "Inicio de cuarto"


# ── Lógica de reconstrucción ──────────────────────────────────────────────────

def _lineup_key(player_ids: set) -> str:
    """Clave canónica de un quinteto: IDs ordenados y concatenados."""
    return "-".join(str(int(p)) for p in sorted(player_ids))


def _seconds_remaining(quarter: int, minute: int, second: int) -> int:
    """Convierte posición en el partido a segundos totales transcurridos."""
    quarter_offset = (quarter - 1) * 600          # cada cuarto = 10 min = 600s
    elapsed_in_quarter = (10 - minute) * 60 - second
    return quarter_offset + elapsed_in_quarter


def _reconstruct_match_lineups(match_id: int, bilbao_role: str,
                                 events_df: pd.DataFrame) -> list[dict]:
    """
    Reconstruye los stints de Bilbao en un partido.

    Retorna lista de dicts con:
      lineup_key, [p1..p5]_id, start_order, end_order,
      start_quarter, score_bilbao_start, score_rival_start,
      score_bilbao_end, score_rival_end
    """
    # Filtrar solo eventos de Bilbao relevantes, ordenados.
    # Usar team_role == bilbao_role (derivado de is_bilbao_home()) en lugar
    # de la columna is_bilbao almacenada, para evitar errores con datos legados.
    df = events_df[
        events_df["team_role"] == bilbao_role
    ].sort_values("order").reset_index(drop=True)

    if df.empty:
        return []

    # Helper: extraer marcador de Bilbao/rival de una fila
    def _scores(row):
        if bilbao_role == "home":
            return int(row["score_home"]), int(row["score_away"])
        return int(row["score_away"]), int(row["score_home"])

    stints = []
    on_court: set[float] = set()
    stint_start_order: int | None = None
    stint_start_quarter: int | None = None
    score_bilbao_start = score_rival_start = 0

    for _, row in df.iterrows():
        desc = row["play_type_desc"]
        pid  = row["player_id"]

        # ── Inicio: quinteto inicial ──────────────────────────────────────────
        if desc == STARTING_FIVE:
            if pd.notna(pid):
                on_court.add(pid)
            # El stint empieza cuando tenemos los 5
            if len(on_court) == 5:
                stint_start_order   = int(row["order"])
                stint_start_quarter = int(row["quarter"])
                sb, sr = _scores(row)
                score_bilbao_start = sb
                score_rival_start  = sr
            continue

        # ── Cambio de cuarto: cerrar stint, continuar con mismo quinteto ─────
        if desc in (QUARTER_END, MATCH_END):
            if on_court and stint_start_order is not None:
                sb, sr = _scores(row)
                stints.append(_make_stint(
                    match_id, on_court,
                    stint_start_order, int(row["order"]),
                    stint_start_quarter,
                    score_bilbao_start, score_rival_start, sb, sr,
                ))
            # Al fin de cuarto cerramos el stint pero NO reiniciamos on_court
            # porque el quinteto puede continuar (o cambiar al inicio del siguiente)
            stint_start_order = None
            continue

        if desc == QUARTER_START:
            # Reabrimos stint con el quinteto actual si hay 5 en pista
            if len(on_court) == 5:
                # Usamos el marcador del evento anterior (el mismo de fin de cuarto)
                stint_start_order   = int(row["order"])
                stint_start_quarter = int(row["quarter"])
                sb, sr = _scores(row)
                score_bilbao_start = sb
                score_rival_start  = sr
            continue

        # ── Sustitución ───────────────────────────────────────────────────────
        if desc in (SUB_IN, SUB_OUT) and pd.notna(pid):
            # Cerrar stint actual antes de aplicar el cambio
            if on_court and len(on_court) == 5 and stint_start_order is not None:
                sb, sr = _scores(row)
                stints.append(_make_stint(
                    match_id, on_court,
                    stint_start_order, int(row["order"]),
                    stint_start_quarter,
                    score_bilbao_start, score_rival_start, sb, sr,
                ))
                stint_start_order = None  # se reabrirá después de procesar todos los cambios del mismo timestamp

            if desc == SUB_IN:
                on_court.add(pid)
            else:
                on_court.discard(pid)

            # Si volvemos a tener 5, abrimos nuevo stint
            if len(on_court) == 5 and stint_start_order is None:
                stint_start_order   = int(row["order"])
                stint_start_quarter = int(row["quarter"])
                sb, sr = _scores(row)
                score_bilbao_start = sb
                score_rival_start  = sr

    return stints


def _make_stint(match_id, on_court, start_order, end_order,
                start_quarter, sb_start, sr_start, sb_end, sr_end) -> dict:
    players = sorted(on_court)
    # Rellenar con None si hay menos de 5 (edge case defensivo)
    while len(players) < 5:
        players.append(None)

    return dict(
        match_id=match_id,
        team_role="bilbao",
        is_bilbao=True,
        p1_id=players[0], p2_id=players[1], p3_id=players[2],
        p4_id=players[3], p5_id=players[4],
        lineup_key=_lineup_key(on_court),
        start_quarter=start_quarter,
        start_order=start_order,
        end_order=end_order,
        score_bilbao_start=sb_start,
        score_rival_start=sr_start,
        score_bilbao_end=sb_end,
        score_rival_end=sr_end,
    )


# ── API pública ───────────────────────────────────────────────────────────────

def rebuild_lineups(engine: Engine) -> int:
    """
    Reconstruye todos los stints de Bilbao para todos los partidos
    y los persiste en la tabla lineups (borra los anteriores primero).
    Retorna el número de stints guardados.
    """
    with engine.connect() as conn:
        matches = conn.execute(
            text("SELECT id, source_file FROM matches ORDER BY date")
        ).fetchall()

    total = 0
    with Session(engine) as session:
        # Limpiar stints previos
        session.query(Lineup).delete()
        session.commit()

        for match_id, source_file in matches:
            # Derivar bilbao_role del nombre de fichero — fuente de verdad
            bilbao_role = "home" if is_bilbao_home(source_file) else "away"
            events_df = pd.read_sql(
                text("""
                    SELECT * FROM events
                    WHERE match_id = :mid
                    ORDER BY "order"
                """),
                engine,
                params={"mid": match_id},
            )

            stints = _reconstruct_match_lineups(match_id, bilbao_role, events_df)

            for s in stints:
                session.add(Lineup(**s))

            total += len(stints)

        session.commit()

    return total


def lineup_stats(engine: Engine, min_stints: int = 2) -> pd.DataFrame:
    """
    Agrega los stints por lineup_key y calcula:
      - net_pts    : diferencial de puntos total
      - net_rating : net_pts / stints (indicativo, no por 100 pos)
      - stints     : número de veces que ese quinteto estuvo en pista
      - jugadores  : nombres de los 5 jugadores

    min_stints filtra quintetos con poca muestra.
    """
    with engine.connect() as conn:
        df = pd.read_sql(
            text("""
                SELECT
                    l.lineup_key,
                    l.p1_id, l.p2_id, l.p3_id, l.p4_id, l.p5_id,
                    (l.score_bilbao_end - l.score_bilbao_start)
                        - (l.score_rival_end  - l.score_rival_start) AS net_pts_stint
                FROM lineups l
                WHERE l.is_bilbao = TRUE
            """),
            conn,
        )

    if df.empty:
        return pd.DataFrame()

    agg = (
        df.groupby(["lineup_key", "p1_id", "p2_id", "p3_id", "p4_id", "p5_id"])
        .agg(
            stints=("net_pts_stint", "count"),
            net_pts=("net_pts_stint", "sum"),
        )
        .reset_index()
    )

    agg = agg[agg["stints"] >= min_stints].copy()
    agg["net_per_stint"] = (agg["net_pts"] / agg["stints"]).round(2)

    # Enriquecer con nombres de jugadores
    player_names = _get_player_names(engine)
    for col in ["p1_id", "p2_id", "p3_id", "p4_id", "p5_id"]:
        agg[col.replace("_id", "_name")] = agg[col].map(player_names)

    return agg.sort_values("net_pts", ascending=False).reset_index(drop=True)


def on_off_splits(engine: Engine) -> pd.DataFrame:
    """
    On/Off splits por jugador de Bilbao.

    Para cada jugador calcula:
      net_pts_on    : diferencial de puntos cuando está en pista
      net_pts_off   : diferencial cuando NO está en pista
      stints_on/off : número de stints en cada condición
      on_off_diff   : net_pts_on - net_pts_off (el número más importante)
    """
    with engine.connect() as conn:
        lineups_df = pd.read_sql(
            text("""
                SELECT
                    l.lineup_key, l.p1_id, l.p2_id, l.p3_id, l.p4_id, l.p5_id,
                    (l.score_bilbao_end - l.score_bilbao_start)
                        - (l.score_rival_end  - l.score_rival_start) AS net_pts
                FROM lineups l
                WHERE l.is_bilbao = TRUE
            """),
            conn,
        )

        bilbao_players = pd.read_sql(
            text("""
                SELECT DISTINCT e.player_id, e.player_name
                FROM events e
                WHERE e.is_bilbao = TRUE AND e.player_id IS NOT NULL
            """),
            conn,
        )

    if lineups_df.empty:
        return pd.DataFrame()

    results = []
    id_cols = ["p1_id", "p2_id", "p3_id", "p4_id", "p5_id"]

    for _, player in bilbao_players.iterrows():
        pid = player["player_id"]
        name = player["player_name"]

        # Stints donde el jugador está en pista
        on_mask = lineups_df[id_cols].isin([pid]).any(axis=1)
        on_df  = lineups_df[on_mask]
        off_df = lineups_df[~on_mask]

        if len(on_df) == 0:
            continue

        net_on  = on_df["net_pts"].sum()
        net_off = off_df["net_pts"].sum() if len(off_df) > 0 else None

        results.append({
            "player_name":   name,
            "player_id":     pid,
            "stints_on":     len(on_df),
            "stints_off":    len(off_df),
            "net_pts_on":    int(net_on),
            "net_pts_off":   int(net_off) if net_off is not None else None,
            "on_off_diff":   int(net_on - net_off) if net_off is not None else None,
        })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    return df.sort_values("net_pts_on", ascending=False).reset_index(drop=True)


def player_impact(engine: Engine) -> pd.DataFrame:
    """
    Tabla resumen combinando On/Off con shooting profile.
    Una sola vista para el cuerpo técnico.
    """
    from analytics.metrics import shooting_profile

    oo  = on_off_splits(engine)
    sp  = shooting_profile(engine, min_games=1)

    if oo.empty or sp.empty:
        return pd.DataFrame()

    merged = oo.merge(
        sp[["player_name", "games", "pts_per_game", "efg_pct", "ts_pct",
            "ast_per_game", "tov_per_game"]],
        on="player_name",
        how="left",
    )

    return merged.sort_values("on_off_diff", ascending=False).reset_index(drop=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_player_names(engine: Engine) -> dict:
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT id, name FROM players"), conn)
    return dict(zip(df["id"], df["name"]))