"""
analytics/validators.py

Validaciones obligatorias antes de cualquier cálculo de métricas.
Si una validación falla → lanzar excepción. No continuar con datos incorrectos.

Usar en pipeline/ingest.py y analytics/metrics.py / analytics/lineups.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Roster oficial (actualizar en cada mercado de fichajes)
# ---------------------------------------------------------------------------
BILBAO_ROSTER_2526: dict[int, str] = {
    2:  "Margiris Normantas",
    3:  "Harald Frey",
    5:  "Bingen Errasti",
    6:  "Aimar Minteguí",
    7:  "Justin Jaworski",
    8:  "Aiert Velasco",
    9:  "Urko Madariaga",
    10: "Martin Krampelj",
    11: "Darrun Hilliard",
    12: "Aleksandar Zecevic",
    13: "Bassala Bagayoko",
    18: "Luke Petrasek",
    19: "Melwin Pantzar",
    20: "Amar Sylla",
    22: "Aleix Font",
    32: "Tryggvi Hlinason",
    73: "Stefan Lazarevic",
}

BILBAO_ROSTER_NAMES: set[str] = set(BILBAO_ROSTER_2526.values())


# ---------------------------------------------------------------------------
# 1. Inferir si Bilbao es local desde el nombre del fichero CSV
# ---------------------------------------------------------------------------
def is_bilbao_home(filename: str | Path) -> bool:
    """
    Determina si Bilbao es el equipo local a partir del nombre del fichero CSV.

    El nombre del fichero es la única fuente de verdad para home/away.
    Formato esperado: YYYYMMDD_matchId_EquipoLocal_vs_EquipoVisitante_plays.csv

    Args:
        filename: Ruta o nombre del fichero CSV.

    Returns:
        True si Bilbao es local, False si es visitante.

    Examples:
        >>> is_bilbao_home("20251026_104492_SurneBilbaoBasket_vs_MoraBancAndorra_plays.csv")
        True
        >>> is_bilbao_home("20251019_104481_JoventutBadalona_vs_SurneBilbaoBasket_plays.csv")
        False
    """
    stem = Path(filename).stem  # quitar extensión
    parts = stem.split("_vs_")
    if len(parts) != 2:
        raise ValueError(
            f"Nombre de fichero no reconocido: '{filename}'. "
            "Formato esperado: YYYYMMDD_matchId_Local_vs_Away_plays.csv"
        )
    home_part = parts[0]
    return "SurneBilbao" in home_part


def get_bilbao_flag(filename: str | Path) -> bool:
    """
    Devuelve el valor de is_local que corresponde a Bilbao en este fichero.
    Alias semántico de is_bilbao_home para uso en filtros de DataFrame.

    Examples:
        >>> flag = get_bilbao_flag("20251019_..._JoventutBadalona_vs_SurneBilbao_plays.csv")
        >>> df_bilbao = df[df["is_local"] == flag]
    """
    return is_bilbao_home(filename)


# ---------------------------------------------------------------------------
# 2. Validar que el schema del CSV es correcto
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "match_id", "quarter", "minute", "second", "is_local",
    "team_role", "play_type", "play_type_desc", "player_name",
    "pts", "fg2_made", "fg2_att", "fg3_made", "fg3_att",
    "ft_made", "ft_att", "assists", "off_reb", "def_reb",
    "steals", "turnovers", "blocks", "fouls",
]


def validate_schema(df: pd.DataFrame, filename: str = "") -> None:
    """
    Verifica que el DataFrame tiene todas las columnas requeridas.

    Raises:
        ValueError: Si faltan columnas requeridas.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{filename}] Columnas faltantes en el CSV: {missing}\n"
            "Verifica que el scraper genera el formato correcto."
        )
    logger.info("[%s] Schema OK — %d filas, %d columnas", filename, len(df), len(df.columns))


# ---------------------------------------------------------------------------
# 3. Validar que los jugadores de Bilbao son del roster oficial
# ---------------------------------------------------------------------------
def validate_bilbao_players(
    df: pd.DataFrame,
    filename: str = "",
    roster: set[str] | None = None,
    strict: bool = False,
) -> None:
    """
    Verifica que los jugadores identificados como Bilbao están en el roster oficial.

    Args:
        df: DataFrame con columna 'is_bilbao' (bool) y 'player_name'.
        filename: Nombre del fichero (para logging).
        roster: Set de nombres válidos. Si None, usa BILBAO_ROSTER_NAMES.
        strict: Si True, lanza excepción. Si False, solo avisa con WARNING.

    Raises:
        ValueError: Si strict=True y hay jugadores no reconocidos.
    """
    if roster is None:
        roster = BILBAO_ROSTER_NAMES

    if "is_bilbao" not in df.columns:
        logger.warning("[%s] Columna 'is_bilbao' no encontrada — saltando validación de roster", filename)
        return

    actual = set(df[df["is_bilbao"].astype(bool)]["player_name"].dropna().unique())
    unexpected = actual - roster

    if unexpected:
        msg = (
            f"[{filename}] JUGADORES NO RECONOCIDOS EN ROSTER BILBAO: {unexpected}\n"
            "Posibles causas:\n"
            "  1. is_bilbao asignado incorrectamente (home/away invertido)\n"
            "  2. Jugador nuevo no añadido al roster en analytics/validators.py\n"
            "  3. Nombre del jugador con variante ortográfica distinta"
        )
        if strict:
            raise ValueError(msg)
        else:
            logger.warning(msg)
    else:
        logger.info("[%s] Roster Bilbao OK — %d jugadores identificados", filename, len(actual))


# ---------------------------------------------------------------------------
# 4. Validar pares de sustituciones
# ---------------------------------------------------------------------------
def validate_substitution_pairs(df: pd.DataFrame, filename: str = "") -> None:
    """
    Verifica que cada 'Sustitución' (112) tiene su 'Entra a pista' (115) correspondiente
    al mismo timestamp, y viceversa.

    Detecta eventos huérfanos que corromperían la reconstrucción de quintetos.
    Solo genera WARNINGs (los datos de ACB a veces tienen pequeñas inconsistencias).
    """
    subs = df[df["play_type"].isin([112, 115])].copy()

    if subs.empty:
        logger.info("[%s] No hay eventos de sustitución en este dataset", filename)
        return

    issues = []
    grouped = subs.groupby(["match_id", "quarter", "minute", "second", "team_role"])

    for key, group in grouped:
        entries = len(group[group["play_type"] == 115])
        exits   = len(group[group["play_type"] == 112])
        if entries != exits:
            issues.append(f"  Q{key[1]} min{key[2]}:{key[3]:02d} [{key[4]}] — {entries} entradas, {exits} salidas")

    if issues:
        logger.warning(
            "[%s] %d sustituciones desbalanceadas:\n%s",
            filename, len(issues), "\n".join(issues)
        )
    else:
        logger.info("[%s] Sustituciones OK — todos los pares balanceados", filename)


# ---------------------------------------------------------------------------
# 5. Detectar duplicación de stats acumulativas
# ---------------------------------------------------------------------------
def validate_stats_not_duplicated(
    df: pd.DataFrame,
    filename: str = "",
    pts_threshold: float = 65.0,
) -> None:
    """
    Heurístico para detectar si se sumaron stats acumulativas en lugar de MAX().
    Si un jugador supera pts_threshold puntos en un partido, hay duplicación.

    Args:
        df: DataFrame con columnas 'player_name' y 'pts', ya agrupado por partido.
        filename: Para logging.
        pts_threshold: Umbral de puntos por encima del cual se sospecha duplicación.
    """
    if "pts" not in df.columns or "player_name" not in df.columns:
        return

    max_pts = df.groupby("player_name")["pts"].sum().max()
    if max_pts > pts_threshold:
        raise ValueError(
            f"[{filename}] POSIBLE DUPLICACIÓN DE STATS: un jugador suma {max_pts:.0f} pts.\n"
            "Verifica que usas MAX() y no SUM() para estadísticas acumulativas del CSV.\n"
            "Los CSVs del scraper ACB son acumulativos dentro del partido."
        )
    logger.info("[%s] Stats OK — máximo %s pts por jugador", filename, max_pts)


# ---------------------------------------------------------------------------
# 6. Runner completo — ejecutar todas las validaciones
# ---------------------------------------------------------------------------
def run_all_validations(
    df: pd.DataFrame,
    filename: str,
    roster: set[str] | None = None,
    strict_roster: bool = False,
) -> None:
    """
    Ejecuta todas las validaciones en orden. Llama a esto antes de ingestar
    cualquier CSV en la BD.

    Args:
        df: DataFrame del CSV parseado.
        filename: Nombre del fichero (determina home/away de Bilbao).
        roster: Set de nombres válidos para Bilbao. Usa BILBAO_ROSTER_NAMES si None.
        strict_roster: Si True, lanza excepción en jugadores no reconocidos.
    """
    logger.info("=== Validando: %s ===", filename)
    validate_schema(df, filename)
    validate_substitution_pairs(df, filename)
    # validate_bilbao_players y validate_stats se ejecutan después de asignar is_bilbao
    logger.info("=== Validación OK: %s ===", filename)
