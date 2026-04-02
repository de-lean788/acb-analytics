---
name: scraping-acb-data
description: >
  Usar cuando se modifica acb_scraper.py o se crea un nuevo scraper
  para obtener datos de la API ACB.
---

## Workflow

```
1. Obtener match_id desde acb.com
2. Fetch con retry + backoff
3. Parse → normalizar a estructura de CSV estándar
4. Validate → naming, schema, jugadores
5. Store → data/csv/
```

## Estructura de fetch robusta

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "X-APIKEY": api_key,
        "User-Agent": "Mozilla/5.0 (compatible; ACB-Analytics/1.0)",
    })
    return session

def fetch_match(session: requests.Session, match_id: int) -> dict:
    """Solo obtiene datos. Sin parsear, sin guardar."""
    url = f"https://api.acb.com/match/{match_id}/plays"
    response = session.get(url, timeout=10)
    response.raise_for_status()
    time.sleep(1)  # rate limiting
    return response.json()
```

## Naming del CSV de salida

```python
def build_csv_filename(match_id: int, date: str, home: str, away: str) -> str:
    """
    Formato: YYYYMMDD_matchId_EquipoLocal_vs_EquipoVisitante_plays.csv
    Crítico: el nombre determina home/away en todo el sistema.
    """
    home_clean = home.replace(" ", "")
    away_clean = away.replace(" ", "")
    return f"{date}_{match_id}_{home_clean}_vs_{away_clean}_plays.csv"
```

## Separación fetch / parse / store

```python
# ✅ Cada función tiene una responsabilidad
raw_data = fetch_match(session, match_id)     # fetch
df = parse_match_plays(raw_data)              # parse
save_csv(df, output_dir, filename)            # store

# ❌ No mezclar todo en una función
```

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| 401/403 | API key caducada | Obtener nueva desde DevTools |
| CSV con jugadores mezclados | Nombre fichero mal formado | Verificar naming |
| Datos acumulativos | Normal en ACB API | Usar MAX() al ingestar |

## Reference

- `acb_scraper.py` — implementación actual
- `.claude/rules/scraping.md` — reglas detalladas

## Token efficiency
- Al depurar un scraper: testear con un único `match_id`, no un rango de partidos
- El output de `fetch_match` no necesita imprimirse completo — loggear solo `match_id` y número de plays
- Si hay error de parsing: mostrar `raw_data[:3]` (primeras entradas), no el JSON completo