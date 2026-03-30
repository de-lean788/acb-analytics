# scraping.md

Aplicar en cambios a `acb_scraper.py` o cualquier nuevo scraper.

## Autenticación ACB

- API requiere `X-APIKEY` obtenida desde DevTools del navegador en acb.com
- La key caduca — si hay 401/403, obtener nueva desde el navegador
- Guardar en `.env`: `ACB_API_KEY=...` — **nunca en código ni en git**

## Nomenclatura de ficheros CSV

```
YYYYMMDD_matchId_EquipoLocal_vs_EquipoVisitante_plays.csv
```

Ejemplo: `20251019_104481_JoventutBadalona_vs_SurneBilbaoBasket_plays.csv`

**El nombre del fichero es la fuente de verdad para home/away.** La función de ingesta DEBE parsearlo.

## Robustez

```python
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Retry con backoff — obligatorio
session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
session.mount("https://", HTTPAdapter(max_retries=retry))

# Rate limiting — no abusar de la API
time.sleep(1)  # entre requests
```

## Separación de responsabilidades

```
fetch()   → solo obtiene HTML/JSON, sin parsear
parse()   → solo parsea, sin efectos en disco
store()   → solo guarda, sin lógica de negocio
```

## IDs del equipo

```python
BILBAO_TEAM_ID = 4389
BILBAO_CLUB_ID = 4
```
