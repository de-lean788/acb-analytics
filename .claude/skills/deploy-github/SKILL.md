---
name: managing-deploy-github
description: >
  Usar cuando se hace deploy a Streamlit Cloud, se gestiona el repo de GitHub,
  o se migra la BD a Supabase.
---

## Workflow de deploy

```
1. pytest tests/ -v               → todos verdes
2. migrate (si hay datos nuevos)  → python migrate_to_supabase.py
3. git push origin master         → deploy automático en Streamlit Cloud
4. verificar en acb-analytics-bilbao.streamlit.app
```

## Secrets y credenciales

```toml
# .streamlit/secrets.toml (local, en .gitignore)
[database]
url = "postgresql+psycopg2://user:pass@host:5432/db"
```

```python
# En código
import streamlit as st
DATABASE_URL = st.secrets["database"]["url"]
```

Producción: Streamlit Cloud > App > Settings > Secrets.

## Errores frecuentes en Streamlit Cloud

```
psycopg2.errors.UndefinedFunction: operator does not exist: boolean = integer
→ WHERE is_bilbao = 1       ← cambiar a: WHERE is_bilbao = TRUE

ProgrammingError: column X must appear in GROUP BY
→ GROUP BY incompleto       ← añadir todas las columnas no agregadas

OperationalError: connection refused
→ Supabase pausado          ← entrar a supabase.com y reactivar el proyecto
```

## Supabase — plan gratuito

- Se pausa automáticamente tras **7 días sin actividad**
- Para reactivar: entrar a `supabase.com` y hacer clic en "Restore project"
- Si el proyecto crece: considerar plan Pro

## Migración a Supabase

```bash
# Migración completa (borra y recrea)
python migrate_to_supabase.py --target 'postgresql+psycopg2://...'

# Parámetros importantes de to_sql()
df.to_sql(
    table_name, engine,
    if_exists="append",
    index=False,
    chunksize=100,          # nunca method="multi" — límite 32.767 parámetros
)
```

## Convenciones de commit

```
fix:      corrección de bug (ej: "fix: booleanos PostgreSQL en lineups")
feat:     nueva funcionalidad (ej: "feat: añadir vista rival analysis")
data:     datos nuevos (ej: "data: añadir partidos J8-J12")
test:     tests (ej: "test: validación jugadores Bilbao")
refactor: sin cambio de comportamiento
```

## Token efficiency
- Antes de hacer deploy: ejecutar `pytest tests/ -q` (no `-v`) — output mínimo suficiente para confirmar
- No leer `migrate_to_supabase.py` completo salvo que el problema sea de migración
- Para verificar deploy: comprobar solo la URL final, no releer ficheros de configuración