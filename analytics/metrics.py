"""
Métricas core — Fase 2
========================
Todas las funciones reciben un engine SQLAlchemy y devuelven DataFrames.
Los stats del CSV son acumulativos por jugador dentro del partido,
por eso usamos MAX() para obtener el boxscore final de cada jugador.

Métricas implementadas:
  - boxscore_bilbao()     : boxscore de Bilbao por partido
  - team_stats()          : totales de equipo por partido
  - four_factors()        : Four Factors (Dean Oliver) por partido
  - shooting_profile()    : eFG%, TS%, FT Rate por jugador (acumulado temporada)
  - net_ratings()         : Off/Def/Net Rating por partido
  - season_summary()      : resumen de temporada con todos los kpis
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# ── Helpers internos ──────────────────────────────────────────────────────────

def _read(engine: Engine, query: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def _boxscore_raw(engine: Engine) -> pd.DataFrame:
    """
    Boxscore de todos los jugadores en todos los partidos.
    Usa MAX() porque los stats del CSV son acumulativos.
    """
    q = """
    SELECT
        m.id            AS match_id,
        m.date,
        m.home_team,
        m.away_team,
        m.bilbao_role,
        m.score_home_final,
        m.score_away_final,
        e.player_id,
        e.player_name,
        e.is_bilbao,
        MAX(e.pts)       AS pts,
        MAX(e.fg2_made)  AS fg2m,
        MAX(e.fg2_att)   AS fg2a,
        MAX(e.fg3_made)  AS fg3m,
        MAX(e.fg3_att)   AS fg3a,
        MAX(e.ft_made)   AS ftm,
        MAX(e.ft_att)    AS fta,
        MAX(e.assists)   AS ast,
        MAX(e.off_reb)   AS orb,
        MAX(e.def_reb)   AS drb,
        MAX(e.tot_reb)   AS trb,
        MAX(e.steals)    AS stl,
        MAX(e.turnovers) AS tov,
        MAX(e.blocks)    AS blk,
        MAX(e.fouls)     AS pf,
        MAX(e.fouls_drawn) AS fd
    FROM events e
    JOIN matches m ON e.match_id = m.id
    WHERE e.player_id IS NOT NULL
    GROUP BY m.id, e.player_id
    ORDER BY m.date, e.is_bilbao DESC, pts DESC
    """
    df = _read(engine, q)

    # Puntos encajados por Bilbao en cada partido
    df["score_bilbao"] = df.apply(
        lambda r: r["score_home_final"] if r["bilbao_role"] == "home" else r["score_away_final"],
        axis=1,
    )
    df["score_rival"] = df.apply(
        lambda r: r["score_away_final"] if r["bilbao_role"] == "home" else r["score_home_final"],
        axis=1,
    )
    df["rival_name"] = df.apply(
        lambda r: r["away_team"] if r["bilbao_role"] == "home" else r["home_team"],
        axis=1,
    )
    df["result"] = df.apply(
        lambda r: "W" if r["score_bilbao"] > r["score_rival"] else "L", axis=1
    )
    return df


# ── API pública ───────────────────────────────────────────────────────────────

def boxscore_bilbao(engine: Engine, match_id: int | None = None) -> pd.DataFrame:
    """
    Boxscore de Bilbao. Si match_id=None devuelve todos los partidos.
    Columnas útiles: date, rival_name, result, player_name, pts, fg2m, fg2a,
                     fg3m, fg3a, ftm, fta, ast, orb, drb, stl, tov, blk, pf
    """
    df = _boxscore_raw(engine)
    df = df[df["is_bilbao"] == 1].copy()
    if match_id:
        df = df[df["match_id"] == match_id]
    return df.reset_index(drop=True)


def team_stats(engine: Engine) -> pd.DataFrame:
    """
    Totales de equipo por partido para Bilbao y el rival.
    Base para calcular Four Factors y Ratings.
    """
    raw = _boxscore_raw(engine)

    def _agg(grp):
        return pd.Series({
            "pts":  grp["pts"].sum(),
            "fg2m": grp["fg2m"].sum(),
            "fg2a": grp["fg2a"].sum(),
            "fg3m": grp["fg3m"].sum(),
            "fg3a": grp["fg3a"].sum(),
            "ftm":  grp["ftm"].sum(),
            "fta":  grp["fta"].sum(),
            "ast":  grp["ast"].sum(),
            "orb":  grp["orb"].sum(),
            "drb":  grp["drb"].sum(),
            "trb":  grp["trb"].sum(),
            "stl":  grp["stl"].sum(),
            "tov":  grp["tov"].sum(),
            "blk":  grp["blk"].sum(),
            "pf":   grp["pf"].sum(),
        })

    bilbao = (
        raw[raw["is_bilbao"] == 1]
        .groupby(["match_id", "date", "rival_name", "result",
                  "score_bilbao", "score_rival"])
        .apply(_agg, include_groups=False)
        .reset_index()
    )
    bilbao["team"] = "Bilbao"

    rival = (
        raw[raw["is_bilbao"] == 0]
        .groupby(["match_id"])
        .apply(_agg, include_groups=False)
        .reset_index()
    )
    rival["team"] = "Rival"

    # Merge para tener ambos equipos en el mismo partido
    merged = bilbao.merge(
        rival[["match_id", "orb", "drb", "tov"]],
        on="match_id",
        suffixes=("_bilbao", "_rival"),
    )

    # Posesiones estimadas (fórmula Dean Oliver)
    # Poss = FGA + 0.44*FTA - ORB + TOV
    merged["fga"] = merged["fg2a"] + merged["fg3a"]
    merged["poss"] = (
        merged["fga"]
        + 0.44 * merged["fta"]
        - merged["orb_bilbao"]
        + merged["tov_bilbao"]
    ).round(1)

    merged["poss_rival"] = (
        (merged["fg2a"] + merged["fg3a"])  # rival fga aproximado con drb de Bilbao
        + 0.44 * merged["fta"]
        - merged["orb_rival"]
        + merged["tov_rival"]
    ).round(1)

    return merged.sort_values("date").reset_index(drop=True)


def four_factors(engine: Engine) -> pd.DataFrame:
    """
    Four Factors de Dean Oliver por partido para Bilbao.

    eFG%   = (FG2M + 1.5*FG3M) / FGA          ponderación triples
    TOV%   = TOV / (FGA + 0.44*FTA + TOV)      % posesiones perdidas
    ORB%   = ORB_bilbao / (ORB_bilbao + DRB_rival)  % rebotes ofensivos capturados
    FT_Rate = FTA / FGA                         agresividad en la línea

    Pesos (Oliver): eFG%=0.4, TOV%=0.25, ORB%=0.20, FT_Rate=0.15
    """
    ts = team_stats(engine)

    # Necesito los rebotes defensivos del rival para ORB%
    raw = _boxscore_raw(engine)
    rival_drb = (
        raw[raw["is_bilbao"] == 0]
        .groupby("match_id")["drb"]
        .sum()
        .reset_index()
        .rename(columns={"drb": "rival_drb"})
    )

    df = ts.merge(rival_drb, on="match_id")

    fga = df["fg2a"] + df["fg3a"]

    df["efg_pct"] = ((df["fg2m"] + 1.5 * df["fg3m"]) / fga).round(4)
    df["tov_pct"] = (df["tov_bilbao"] / (fga + 0.44 * df["fta"] + df["tov_bilbao"])).round(4)
    df["orb_pct"] = (df["orb_bilbao"] / (df["orb_bilbao"] + df["rival_drb"])).round(4)
    df["ft_rate"] = (df["fta"] / fga).round(4)

    # Score compuesto (orientativo, no oficial)
    df["ff_score"] = (
        0.40 * df["efg_pct"]
        - 0.25 * df["tov_pct"]
        + 0.20 * df["orb_pct"]
        + 0.15 * df["ft_rate"]
    ).round(4)

    cols = ["date", "rival_name", "result", "score_bilbao", "score_rival",
            "efg_pct", "tov_pct", "orb_pct", "ft_rate", "ff_score",
            "pts", "poss"]
    return df[cols].sort_values("date").reset_index(drop=True)


def shooting_profile(engine: Engine, min_games: int = 2) -> pd.DataFrame:
    """
    Perfil de tiro de cada jugador de Bilbao (acumulado de temporada).
    Solo jugadores con >= min_games partidos.

    eFG%  = (FG2M + 1.5*FG3M) / FGA
    TS%   = PTS / (2 * (FGA + 0.44*FTA))
    FT_Rate = FTA / FGA
    3PAr  = FG3A / FGA   (tasa de triples sobre intentos)
    """
    raw = _boxscore_raw(engine)
    bilbao = raw[raw["is_bilbao"] == 1].copy()

    agg = (
        bilbao.groupby("player_name")
        .agg(
            games=("match_id", "nunique"),
            pts=("pts", "sum"),
            fg2m=("fg2m", "sum"),
            fg2a=("fg2a", "sum"),
            fg3m=("fg3m", "sum"),
            fg3a=("fg3a", "sum"),
            ftm=("ftm", "sum"),
            fta=("fta", "sum"),
            ast=("ast", "sum"),
            orb=("orb", "sum"),
            drb=("drb", "sum"),
            stl=("stl", "sum"),
            tov=("tov", "sum"),
            blk=("blk", "sum"),
        )
        .reset_index()
    )

    agg = agg[agg["games"] >= min_games].copy()

    fga = agg["fg2a"] + agg["fg3a"]
    agg["fga"] = fga
    agg["efg_pct"]  = ((agg["fg2m"] + 1.5 * agg["fg3m"]) / fga).round(4)
    agg["ts_pct"]   = (agg["pts"] / (2 * (fga + 0.44 * agg["fta"]))).round(4)
    agg["ft_rate"]  = (agg["fta"] / fga).round(4)
    agg["3par"]     = (agg["fg3a"] / fga).round(4)
    agg["ast_per_game"] = (agg["ast"] / agg["games"]).round(2)
    agg["pts_per_game"] = (agg["pts"] / agg["games"]).round(2)
    agg["tov_per_game"] = (agg["tov"] / agg["games"]).round(2)

    return agg.sort_values("pts_per_game", ascending=False).reset_index(drop=True)


def net_ratings(engine: Engine) -> pd.DataFrame:
    """
    Offensive / Defensive / Net Rating por partido.
    Normalizados a 100 posesiones.

    ORtg = (Pts_bilbao / Poss_bilbao) * 100
    DRtg = (Pts_rival  / Poss_rival)  * 100
    NRtg = ORtg - DRtg
    """
    ts = team_stats(engine)

    # Puntos del rival por partido
    raw = _boxscore_raw(engine)
    rival_pts = (
        raw[raw["is_bilbao"] == 0]
        .groupby("match_id")["pts"]
        .sum()
        .reset_index()
        .rename(columns={"pts": "pts_rival_sum"})
    )

    df = ts.merge(rival_pts, on="match_id")

    # Usar el marcador final como fuente de verdad para los puntos
    df["ortg"] = ((df["score_bilbao"] / df["poss"]) * 100).round(1)
    df["drtg"] = ((df["score_rival"]  / df["poss_rival"]) * 100).round(1)
    df["nrtg"] = (df["ortg"] - df["drtg"]).round(1)

    cols = ["date", "rival_name", "result", "score_bilbao", "score_rival",
            "poss", "ortg", "drtg", "nrtg"]
    return df[cols].sort_values("date").reset_index(drop=True)


def season_summary(engine: Engine) -> dict:
    """
    KPIs de temporada. Devuelve un dict con DataFrames y valores escalares.
    Útil como entrada para el dashboard.
    """
    ff = four_factors(engine)
    nr = net_ratings(engine)
    sp = shooting_profile(engine, min_games=1)

    wins = (ff["result"] == "W").sum()
    losses = (ff["result"] == "L").sum()

    return {
        "record": f"{wins}W - {losses}L",
        "wins": int(wins),
        "losses": int(losses),
        "avg_ortg": round(nr["ortg"].mean(), 1),
        "avg_drtg": round(nr["drtg"].mean(), 1),
        "avg_nrtg": round(nr["nrtg"].mean(), 1),
        "avg_efg":  round(ff["efg_pct"].mean(), 4),
        "avg_tov":  round(ff["tov_pct"].mean(), 4),
        "avg_orb":  round(ff["orb_pct"].mean(), 4),
        "avg_ft_rate": round(ff["ft_rate"].mean(), 4),
        "four_factors": ff,
        "net_ratings": nr,
        "shooting_profile": sp,
    }
