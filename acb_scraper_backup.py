"""
ACB Play-by-Play Scraper - Surne Bilbao (o cualquier equipo)

ENDPOINTS CONFIRMADOS:
  play-by-play: https://api2.acb.com/api/matchdata/PlayByPlay/play-by-play?matchId=XXXXX
  match-header: https://api2.acb.com/api/matchdata/MatchHeader/match-header?matchId=XXXXX

IMPORTANTE: La X-APIKEY cambia cada sesión de navegador.
Cópiala de DevTools cada vez que la necesites y pásala con --apikey.

EQUIPO SURNE BILBAO:
  team-id: 4389
  club-id: 4 (en la URL de acb.com)

USO:
  # Test un partido
  python acb_scraper.py --team-id 4389 --match-id 104658 --apikey TU_APIKEY --output data/

  # Varios partidos con lista manual de IDs (mientras buscas el endpoint de calendario)
  python acb_scraper.py --team-id 4389 --match-ids 104658,104500,104300 --apikey TU_APIKEY --output data/

  # Temporada completa (requiere confirmar endpoint de calendario con DevTools)
  python acb_scraper.py --team-id 4389 --season 2526 --apikey TU_APIKEY --output data/

  # Inspeccionar un endpoint directamente
  python acb_scraper.py --inspect "https://api2.acb.com/api/..." --apikey TU_APIKEY
"""

import requests
import json
import csv
import time
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

BASE_URL = "https://api2.acb.com/api"

ENDPOINTS = {
    "match_header":  f"{BASE_URL}/matchdata/MatchHeader/match-header?matchId={{match_id}}",
    "play_by_play":  f"{BASE_URL}/matchdata/PlayByPlay/play-by-play?matchId={{match_id}}",
    # ⚠️ Calendario PENDIENTE — busca en DevTools la llamada que devuelve lista de partidos
    # cuando navegas por acb.com/club/partidos/id/4
    # Candidatos probables:
    #   /competition/Calendar/calendar?competitionId=1&seasonId=2526
    #   /competition/matchlist?competitionId=1&seasonId=2526&format=round
    #   /club/matches?clubId=4&seasonId=2526
    "calendar": f"{BASE_URL}/competition/Calendar/calendar?competitionId=1&seasonId={{season_id}}",
}

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://live.acb.com/",
    "Origin": "https://live.acb.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "DNT": "1",
}

DELAY_BETWEEN_REQUESTS = 1.5


# ─── PLAY TYPES ───────────────────────────────────────────────────────────────

PLAY_TYPES = {
    92: "Tiro libre anotado",
    93: "2 puntos anotado (local)",
    94: "3 puntos anotado",
    96: "Tiro libre fallado",
    97: "Tiro de 2 fallado",
    98: "Tiro de 3 fallado",
    100: "2 puntos anotado (visitante)",
    101: "Rebote ofensivo",
    102: "Tapón",
    103: "Robo",
    104: "Rebote defensivo",
    105: "Mate/Bandeja fallada",
    107: "Asistencia",
    108: "Asistencia en 3",
    109: "Falta técnica",
    110: "Falta recibida",
    112: "Sustitución",
    113: "Tiempo muerto",
    115: "Entra a pista",
    116: "Fin de cuarto",
    119: "Asistencia en TL",
    121: "Inicio de cuarto",
    122: "Inicio del partido",
    123: "Fin del partido",
    159: "Falta personal",
    160: "Falta en ataque",
    161: "Falta antideportiva",
    162: "Falta descalificante",
    166: "Falta flagrante",
    178: "Posesión inicial (ganada)",
    179: "Posesión inicial (perdida)",
    410: "Descalificado por 5 faltas",
    416: "Challenge entrenador",
    417: "Challenge visitante",
    533: "Falta de 5 segundos",
    540: "Falta de 3 segundos",
    599: "Quinteto inicial",
    600: "Minuto (marcador parcial)",
    748: "Video review",
    749: "Video review visitante",
}


# ─── MODELOS ──────────────────────────────────────────────────────────────────

@dataclass
class PlayEvent:
    match_id:       int
    quarter:        int
    minute:         int
    second:         int
    time_str:       str
    is_local:       bool
    team_role:      str           # "home" | "away"
    score_home:     int
    score_away:     int
    play_type:      int
    play_type_desc: str
    play_tag:       Optional[int]
    player_name:    Optional[str]
    player_id:      Optional[int]
    player_number:  Optional[str]
    pts:            Optional[int]
    ft_made:        Optional[int]
    ft_att:         Optional[int]
    fg2_made:       Optional[int]
    fg2_att:        Optional[int]
    fg3_made:       Optional[int]
    fg3_att:        Optional[int]
    assists:        Optional[int]
    off_reb:        Optional[int]
    def_reb:        Optional[int]
    tot_reb:        Optional[int]
    steals:         Optional[int]
    turnovers:      Optional[int]
    blocks:         Optional[int]
    fouls:          Optional[int]
    fouls_drawn:    Optional[int]
    order:          int
    raw:            dict = field(default_factory=dict, repr=False)


@dataclass
class MatchInfo:
    match_id:       int
    home_team_id:   int
    home_team_name: str
    away_team_id:   int
    away_team_name: str
    date:           str
    status:         str
    home_score:     int
    away_score:     int
    plays:          list = field(default_factory=list)


# ─── CLIENTE HTTP ─────────────────────────────────────────────────────────────

class ACBClient:
    def __init__(self, apikey: str):
        self.session = requests.Session()
        headers = dict(BASE_HEADERS)
        headers["X-APIKEY"] = apikey
        self.session.headers.update(headers)

    def get(self, url: str) -> dict | list | None:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            log.error(f"HTTP {e.response.status_code} — {url}")
            if e.response.status_code == 401:
                log.error("API key inválida o caducada. Copia una nueva de DevTools con --apikey")
            return None
        except requests.RequestException as e:
            log.error(f"Error de red: {e}")
            return None
        except json.JSONDecodeError:
            log.error(f"Respuesta no es JSON: {url}")
            return None
        finally:
            time.sleep(DELAY_BETWEEN_REQUESTS)


# ─── PARSERS ──────────────────────────────────────────────────────────────────

def parse_match_header(data: dict) -> MatchInfo:
    teams = data.get("teams", {})
    home  = teams.get("home", {})
    away  = teams.get("away", {})
    return MatchInfo(
        match_id       = data["matchId"],
        home_team_id   = home.get("id"),
        home_team_name = home.get("fullName", ""),
        away_team_id   = away.get("id"),
        away_team_name = away.get("fullName", ""),
        date           = data.get("start", ""),
        status         = data.get("matchStatus", ""),
        home_score     = data.get("currentHomeScore", 0),
        away_score     = data.get("currentAwayScore", 0),
    )


def parse_play_by_play(match_id: int, data: dict) -> list[PlayEvent]:
    raw_plays = data.get("plays", [])
    events = []
    for p in raw_plays:
        play_type = p.get("playType", 0)
        q    = p.get("quarter", 0)
        min_ = p.get("minute", 0)
        sec  = p.get("second", 0)
        stats = p.get("playerStats") or {}
        event = PlayEvent(
            match_id       = match_id,
            quarter        = q,
            minute         = min_,
            second         = sec,
            time_str       = f"Q{q} {min_:02d}:{sec:02d}",
            is_local       = p.get("local", False),
            team_role      = "home" if p.get("local", False) else "away",
            score_home     = p.get("scoreHome", 0),
            score_away     = p.get("scoreAway", 0),
            play_type      = play_type,
            play_type_desc = PLAY_TYPES.get(play_type, f"Tipo {play_type}"),
            play_tag       = p.get("playTag"),
            player_name    = p.get("playerName"),
            player_id      = p.get("playerLicenseId"),
            player_number  = p.get("playerNumber"),
            pts            = stats.get("points"),
            ft_made        = stats.get("freeThrowsMade"),
            ft_att         = stats.get("freeThrowsAttempted"),
            fg2_made       = stats.get("twoPointersMade"),
            fg2_att        = stats.get("twoPointersAttempted"),
            fg3_made       = stats.get("threePointersMade"),
            fg3_att        = stats.get("threePointersAttempted"),
            assists        = stats.get("assists"),
            off_reb        = stats.get("offRebounds"),
            def_reb        = stats.get("defRebounds"),
            tot_reb        = stats.get("totalRebounds"),
            steals         = stats.get("steals"),
            turnovers      = stats.get("turnovers"),
            blocks         = stats.get("blocks"),
            fouls          = stats.get("personalFouls"),
            fouls_drawn    = stats.get("foulsDrawn"),
            order          = p.get("order", 0),
            raw            = p,
        )
        events.append(event)
    events.sort(key=lambda e: (e.quarter, -e.minute, -e.second, e.order))
    log.info(f"  → {len(events)} eventos parseados")
    return events


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

class ACBScraper:
    def __init__(self, team_id: int, season_id: str, output_dir: Path, apikey: str):
        self.team_id    = team_id
        self.season_id  = season_id
        self.output_dir = output_dir
        self.client     = ACBClient(apikey)
        output_dir.mkdir(parents=True, exist_ok=True)

    def get_team_match_ids(self) -> list[int]:
        """
        Obtiene matchIds del equipo.
        ⚠️  Endpoint de calendario PENDIENTE de confirmar con DevTools.
        Navega por acb.com/club/partidos/id/4 (Bilbao = club 4) y busca
        la llamada a api2.acb.com que devuelva lista de partidos.
        """
        url = ENDPOINTS["calendar"].format(season_id=self.season_id)
        log.info(f"Cargando calendario: {url}")
        data = self.client.get(url)

        if not data:
            log.error("No se pudo obtener el calendario.")
            log.error("Usa --inspect para explorar el endpoint correcto.")
            return []

        # Guardar JSON crudo para inspección
        debug_path = self.output_dir / "debug_calendar.json"
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"JSON de calendario guardado en {debug_path} — inspecciona la estructura")

        # Intento genérico de extraer matchIds
        match_ids = []
        matches = data if isinstance(data, list) else (
            data.get("matches") or data.get("calendar") or
            data.get("rounds") or data.get("games") or []
        )

        # Si es lista de jornadas con partidos dentro
        if matches and isinstance(matches[0], dict) and "matches" in matches[0]:
            flat = []
            for round_ in matches:
                flat.extend(round_.get("matches", []))
            matches = flat

        for match in matches:
            home_id = (match.get("homeTeamId") or match.get("localTeamId") or
                       (match.get("teams", {}) or {}).get("home", {}).get("id"))
            away_id = (match.get("awayTeamId") or match.get("visitorTeamId") or
                       (match.get("teams", {}) or {}).get("away", {}).get("id"))
            if self.team_id in (home_id, away_id):
                mid = match.get("matchId") or match.get("id")
                if mid:
                    match_ids.append(mid)

        log.info(f"Encontrados {len(match_ids)} partidos para team_id={self.team_id}")
        return match_ids

    def scrape_match(self, match_id: int) -> MatchInfo | None:
        log.info(f"Descargando partido {match_id}...")
        header_data = self.client.get(
            ENDPOINTS["match_header"].format(match_id=match_id)
        )
        if not header_data:
            return None
        match = parse_match_header(header_data)

        pbp_data = self.client.get(
            ENDPOINTS["play_by_play"].format(match_id=match_id)
        )
        if pbp_data:
            match.plays = parse_play_by_play(match_id, pbp_data)
        else:
            log.warning(f"  Sin play-by-play para {match_id}")
        return match

    def run(self, match_ids: list[int] | None = None):
        if match_ids is None:
            match_ids = self.get_team_match_ids()
        if not match_ids:
            log.error("Sin partidos. Usa --match-id o --match-ids para test.")
            return

        all_matches, all_plays = [], []
        for match_id in match_ids:
            match = self.scrape_match(match_id)
            if match:
                all_matches.append(match)
                all_plays.extend(match.plays)

        self._save_json(all_matches)
        self._save_csv(all_plays)
        log.info(f"✅ {len(all_matches)} partidos, {len(all_plays)} eventos guardados")

    def _save_json(self, matches: list[MatchInfo]):
        path = self.output_dir / f"team_{self.team_id}_season_{self.season_id}.json"
        output = []
        for m in matches:
            d = asdict(m)
            for play in d.get("plays", []):
                play.pop("raw", None)
            output.append(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        log.info(f"JSON → {path}")

    def _save_csv(self, plays: list[PlayEvent]):
        if not plays:
            return
        path   = self.output_dir / f"plays_team_{self.team_id}_season_{self.season_id}.csv"
        fields = [k for k in asdict(plays[0]).keys() if k != "raw"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for p in plays:
                row = asdict(p)
                row.pop("raw", None)
                writer.writerow(row)
        log.info(f"CSV  → {path}")


# ─── ENTRYPOINT ───────────────────────────────────────────────────────────────

def inspect_endpoint(url: str, apikey: str):
    client = ACBClient(apikey)
    data   = client.get(url)
    if data:
        text = json.dumps(data, ensure_ascii=False, indent=2)
        print(text[:4000])
        print(f"\n... ({len(text)} chars totales)")
    else:
        print("Sin respuesta o error")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ACB Scraper — Surne Bilbao")
    parser.add_argument("--team-id",   type=int,  default=4389,
                        help="ID del equipo (default: 4389 Surne Bilbao)")
    parser.add_argument("--season",    type=str,  default="2526")
    parser.add_argument("--output",    type=str,  default="data/")
    parser.add_argument("--apikey",    type=str,  required=True,
                        help="X-APIKEY de DevTools (cambia cada sesión)")
    parser.add_argument("--inspect",   type=str,
                        help="Inspeccionar un endpoint directamente")
    parser.add_argument("--match-id",  type=int,
                        help="Scrapear solo un partido (test)")
    parser.add_argument("--match-ids", type=str,
                        help="Lista de matchIds separados por coma")
    args = parser.parse_args()

    out = Path(args.output)

    if args.inspect:
        inspect_endpoint(args.inspect, args.apikey)

    elif args.match_id:
        scraper = ACBScraper(args.team_id, args.season, out, args.apikey)
        match = scraper.scrape_match(args.match_id)
        if match:
            print(f"\n{'='*55}")
            print(f"Partido {match.match_id}: {match.home_team_name} vs {match.away_team_name}")
            print(f"Resultado: {match.home_score}-{match.away_score} | Jugadas: {len(match.plays)}")
            print(f"{'='*55}")
            scoring = [p for p in match.plays if p.play_type in (92, 93, 94, 100)]
            print("\nÚltimas 10 canastas/libres:")
            for p in scoring[-10:]:
                team = match.home_team_name if p.is_local else match.away_team_name
                print(f"  {p.time_str} | {team:20s} | {p.play_type_desc:25s} | "
                      f"{p.player_name or '':20s} | {p.score_home}-{p.score_away}")
            scraper.run(match_ids=[args.match_id])

    elif args.match_ids:
        ids = [int(x.strip()) for x in args.match_ids.split(",")]
        scraper = ACBScraper(args.team_id, args.season, out, args.apikey)
        scraper.run(match_ids=ids)

    else:
        scraper = ACBScraper(args.team_id, args.season, out, args.apikey)
        scraper.run()