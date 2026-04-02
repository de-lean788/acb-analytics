---
name: building-data-pipeline
description: >
  Usar cuando se crea o modifica lógica de ingesta, transformación o almacenamiento
  de datos ACB (pipeline/ingest.py, db/models.py, migrate_to_supabase.py).
---

## Workflow

```
1. Ingest      → leer CSV, parsear nombre fichero (home/away)
2. Validate    → schema, jugadores Bilbao, pares de sustitución
3. Transform   → MAX() stats acumulativas, booleanos correctos
4. Store       → SQLite (local) / Supabase PostgreSQL (cloud)
5. Verify      → pytest, conteo de filas, spot-check manual
```

## Paso 1 — Inferir home/away del nombre del fichero

```python
def is_bilbao_home(filename: str) -> bool:
    """El nombre del CSV es la fuente de verdad para home/away."""
    home_team = Path(filename).stem.split("_vs_")[0].split("_", 2)[-1]
    return "SurneBilbao" in home_team
```

## Paso 2 — Validaciones (ejecutar antes de insertar en BD)

```python
def validate_schema(df: pd.DataFrame) -> None:
    required = ["match_id","quarter","minute","second","is_local",
                "play_type","player_name","pts","fg2_made","fg3_made"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Columnas faltantes: {missing}")

def validate_bilbao_players(df: pd.DataFrame, roster: set[str]) -> None:
    bilbao_players = set(df[df["is_bilbao"]]["player_name"].dropna().unique())
    unexpected = bilbao_players - roster
    if unexpected:
        raise ValueError(f"Jugadores no reconocidos en roster Bilbao: {unexpected}")

def validate_substitution_pairs(df: pd.DataFrame) -> None:
    subs = df[df["play_type"].isin([112, 115])]
    for key, g in subs.groupby(["match_id","quarter","minute","second","team_role"]):
        if len(g[g["play_type"]==115]) != len(g[g["play_type"]==112]):
            logging.warning(f"Sustitución desbalanceada en {key}")
```

## Paso 3 — Transformación correcta de stats

```python
# Stats acumulativas → MAX por jugador por partido
stats = (
    df.groupby(["match_id", "player_id"])
    .agg(pts=("pts", "max"), fg2_made=("fg2_made", "max"), ...)
    .reset_index()
)
```

## Paso 4 — Inserción PostgreSQL

```python
# chunksize=100 para no superar límite de 32.767 parámetros
df.to_sql("events", engine, if_exists="append", index=False, chunksize=100)

# Booleanos: convertir antes de insertar
df["is_bilbao"] = df["is_bilbao"].astype(bool)  # no 0/1
```

## Paso 5 — Verificación

```bash
pytest tests/test_ingest.py -v
python -c "from db.models import engine; ..."  # conteo de filas
```

## Reference

- `pipeline/ingest.py` — implementación actual
- `db/models.py` — esquema de tablas
- `.claude/rules/data-quality.md` — reglas detalladas

## Token efficiency
- Para inspeccionar CSVs: `pd.read_csv(f, nrows=100)` en exploración, nunca el fichero completo
- El log de ingesta debe mostrar conteo de filas y errores, no el DataFrame
- Si falla una validación: mostrar solo los registros problemáticos (`df[mask].head(10)`), no todo el df
- Verificación post-ingesta: un `SELECT COUNT(*)` es suficiente para confirmar, no un `SELECT *`