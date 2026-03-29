# Surne Bilbao Analytics

Pipeline de análisis de datos ACB para el cuerpo técnico del Surne Bilbao Basket.

## Estructura del proyecto

```
bilbao_analytics/
├── data/
│   ├── csv/          ← pon aquí todos los CSVs del scraper
│   └── db/           ← la BD SQLite se genera aquí (bilbao.db)
├── db/
│   └── models.py     ← esquema de tablas (SQLAlchemy)
├── pipeline/
│   └── ingest.py     ← ingesta CSVs → SQLite
├── tests/
│   └── test_ingest.py
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
└── migrate_to_supabase.py
```

## Setup local (sin Docker)

```bash
# 1. Clona / copia el proyecto
cd bilbao_analytics

# 2. Crea el entorno virtual e instala dependencias
make setup

# 3. Activa el entorno
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# 4. Copia tus CSVs
cp /ruta/a/tus/csvs/*_plays.csv data/csv/

# 5. Carga todo en la BD
make ingest
```

## Setup con Docker

```bash
# Levanta la BD y el contenedor de analytics
make docker-up

# Carga los CSVs (los CSVs deben estar en data/csv/)
make docker-ingest

# Adminer (inspector visual de la BD) → http://localhost:8080
# Sistema: SQLite | Base de datos: /db/bilbao.db
```

## Comandos útiles

```bash
make ingest          # carga CSVs nuevos (idempotente, no duplica)
make ingest-reset    # borra la BD y recarga todo desde cero
make db-check        # muestra conteo de tablas
make db-shell        # abre SQLite interactivo
make test            # ejecuta los tests
```

## Variables de entorno (.env)

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | URL de conexión SQLAlchemy | `sqlite:///./data/db/bilbao.db` |
| `BILBAO_TEAM_KEYWORD` | Keyword en el nombre del fichero para identificar a Bilbao | `SurneBilbao` |

## Fases del proyecto

| Fase | Estado | Descripción |
|---|---|---|
| 1 — Pipeline | ✅ | Ingesta, limpieza, modelo de datos |
| 2 — Métricas core | 🔜 | Four Factors, Ratings, Shooting profile |
| 3 — On/Off & Lineups | 🔜 | Reconstrucción de quintetos, Net Rating por lineup |
| 4 — Dashboard | 🔜 | Streamlit para el cuerpo técnico |
