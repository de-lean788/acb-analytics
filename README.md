# Surne Bilbao Analytics

Pipeline de análisis de datos ACB del Surne Bilbao Basket.
Dashboard interactivo con métricas avanzadas de baloncesto desplegado en Streamlit Cloud.

## Estructura del proyecto

```
acb/
├── analytics/
│   ├── lineups.py        ← Reconstrucción de quintetos, On/Off splits
│   └── metrics.py        ← Four Factors, Net Rating, Shooting Profile
├── dashboard/
│   ├── app.py            ← Punto de entrada Streamlit
│   ├── charts.py         ← Helpers de visualización (Plotly)
│   └── views/
│       ├── player_impact.py    ← Vista 1: Impacto de jugadores
│       ├── season_trends.py    ← Vista 2: Tendencia de temporada
│       ├── last_match.py       ← Vista 3: Último partido
│       └── rival_analysis.py   ← Vista 4: Análisis de rival
├── data/
│   ├── csv/              ← CSVs del scraper (no incluidos en repo)
│   └── db/               ← BD SQLite local (no incluida en repo)
├── db/
│   └── models.py         ← Esquema de tablas SQLAlchemy
├── pipeline/
│   └── ingest.py         ← Ingesta CSVs → BD
├── tests/
│   ├── fixtures.py
│   ├── test_ingest.py
│   ├── test_lineups.py
│   └── test_metrics.py
├── .streamlit/
│   └── secrets.toml      ← Credenciales locales (no incluido en repo)
├── migrate_to_supabase.py  ← Migración SQLite → Supabase PostgreSQL
├── acb_scraper.py          ← Scraper de datos ACB
├── requirements.txt
├── Makefile
├── Dockerfile
└── docker-compose.yml
```

## Setup local

```bash
# 1. Clona el repo
git clone https://github.com/de-lean788/acb-analytics
cd acb-analytics

# 2. Crea el entorno virtual e instala dependencias
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Crea el fichero de secrets local
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
DATABASE_URL = "sqlite:///./data/db/bilbao.db"
BILBAO_TEAM_KEYWORD = "SurneBilbao"
EOF

# 4. Crea los directorios de datos
mkdir -p data/csv data/db

# 5. Copia tus CSVs del scraper
cp /ruta/a/tus/csvs/*_plays.csv data/csv/

# 6. Carga los datos en la BD
python -m pipeline.ingest --dir data/csv

# 7. Lanza el dashboard
streamlit run dashboard/app.py
```

## Migración a Supabase (para deploy en cloud)

Necesaria para desplegar en Streamlit Cloud, ya que SQLite no persiste en entornos serverless.

```bash
# Ejecutar desde el directorio raíz del proyecto
python migrate_to_supabase.py --target 'postgresql+psycopg2://usuario:pass@host:5432/postgres'
```

La URL de conexión se obtiene en Supabase → proyecto → botón **Connect** → Session pooler.

Si la contraseña tiene caracteres especiales, URL-encodearla primero:

```bash
python3 << 'EOF'
from urllib.parse import quote
password = 'tu_password_aqui'
print(quote(password, safe=''))
EOF
```

## Deploy en Streamlit Cloud

1. Sube el repo a GitHub (público o privado)
2. Ve a [share.streamlit.io](https://share.streamlit.io) → New app
3. Selecciona el repo, branch `master`, main file `dashboard/app.py`
4. En **Advanced settings → Secrets** añade:

```toml
DATABASE_URL = "postgresql+psycopg2://usuario:pass@host:5432/postgres"
BILBAO_TEAM_KEYWORD = "SurneBilbao"
```

5. Selecciona Python **3.11** (3.14 no es compatible con psycopg2)
6. Deploy

## Comandos útiles (Makefile)

```bash
make ingest          # carga CSVs nuevos (idempotente)
make ingest-reset    # borra la BD y recarga todo
make dashboard       # lanza el dashboard local
make test            # ejecuta los tests
make db-check        # muestra conteo de tablas
make db-shell        # abre SQLite interactivo
```

## Añadir nuevos partidos

```bash
# 1. Scrapear los partidos nuevos con acb_scraper.py
# 2. Copiar los CSVs generados a data/csv/
# 3. Ingestar (solo carga los partidos nuevos, no duplica)
python -m pipeline.ingest --dir data/csv
# 4. Migrar a Supabase para actualizar el dashboard en cloud
python migrate_to_supabase.py --target 'postgresql+psycopg2://...'
```

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | URL de conexión SQLAlchemy | `sqlite:///./data/db/bilbao.db` |
| `BILBAO_TEAM_KEYWORD` | Keyword en el nombre del CSV para identificar a Bilbao | `SurneBilbao` |

## Fases del proyecto

| Fase | Estado | Descripción |
|---|---|---|
| 1 — Pipeline | ✅ | Ingesta CSVs, limpieza, modelo de datos SQLite/PostgreSQL |
| 2 — Métricas core | ✅ | Four Factors, eFG%, TS%, Net/Off/Def Rating, Shooting profile |
| 3 — On/Off & Lineups | ✅ | Reconstrucción de quintetos, Net Rating por lineup, impacto jugador |
| 4 — Dashboard | ✅ | Streamlit con 4 vistas, dark theme, exportación CSV |
| Deploy cloud | ✅ | Supabase PostgreSQL + Streamlit Community Cloud |