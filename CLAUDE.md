# 🏀 Surne Bilbao Analytics

Plataforma de analytics ACB para el cuerpo técnico del **Surne Bilbao Basket** (Liga Endesa 2025-26).
Los outputs se usan en decisiones reales de entrenamiento y táctica — los datos deben ser correctos, verificables y reproducibles.

---

## 🚨 REGLAS CRÍTICAS (leer antes de tocar código)

1. **Nunca hardcodear `is_local == True` para filtrar jugadores de Bilbao** — Bilbao puede ser visitante. Usar siempre el nombre del fichero CSV.
2. **Stats acumulativas → `MAX()`, nunca `SUM()`** — los CSVs son acumulativos dentro del partido.
3. **Booleanos PostgreSQL** → `TRUE/FALSE` en SQL, `True/False` en Python. Nunca `0/1`.
4. **`st.stop()` dentro de tabs mata el rendering** — usar `return`.
5. **No hacer push sin pasar `pytest tests/ -v`**.
6. **No hardcodear credenciales** — `.env` local, Streamlit secrets en producción.
7. **Nunca trabajar en `master` ni en `develop` directamente** — siempre rama `feature/` o `fix/`.

> Detalle de cada regla en `.claude/rules/`.

---

## 🎯 Contexto de negocio

- **Usuario final**: ayudante técnico. Entiende baloncesto, no estadística avanzada.
- **Principio**: toda métrica lleva explicación en lenguaje de baloncesto.
- **Criticidad**: informes con datos reales — un dato incorrecto tiene impacto real en el equipo.

---

## 🧱 Arquitectura

```
acb-analytics/
├── db/models.py              ← SQLAlchemy ORM: Match, Player, Event, Lineup
├── pipeline/ingest.py        ← CSV → SQLite/PostgreSQL (idempotente)
├── analytics/
│   ├── metrics.py            ← Four Factors, eFG%, TS%, Net/Off/Def Rating
│   ├── lineups.py            ← Reconstrucción quintetos, On/Off splits
│   └── validators.py         ← Validaciones obligatorias pre-análisis
├── dashboard/
│   ├── app.py                ← Streamlit entry point
│   └── views/                ← player_impact, season_trends, last_match, rival_analysis
├── tests/                    ← pytest
├── acb_scraper.py            ← Scraper ACB API
└── migrate_to_supabase.py    ← SQLite → Supabase PostgreSQL
```

### Pipeline de datos

```
scrape → raw CSV → ingest → validate → store → analytics → dashboard
```

---

## 🔧 Stack

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.12 |
| Dashboard | Streamlit 1.41 + Plotly |
| BD local | SQLite (SQLAlchemy ORM) |
| BD producción | Supabase PostgreSQL |
| Deploy | Streamlit Community Cloud |
| Repo | `github.com/de-lean788/acb-analytics` (público) |
| Scraper | Python custom → ACB API (`X-APIKEY` desde DevTools) |

---

## 📊 Datos del equipo

```python
BILBAO_TEAM_ID = 4389
BILBAO_CLUB_ID = 4

BILBAO_ROSTER_2526 = {
    2: "Margiris Normantas",   3: "Harald Frey",
    5: "Bingen Errasti",       6: "Aimar Minteguí",
    7: "Justin Jaworski",      8: "Aiert Velasco",
    9: "Urko Madariaga",       10: "Martin Krampelj",
    11: "Darrun Hilliard",     12: "Aleksandar Zecevic",
    13: "Bassala Bagayoko",    18: "Luke Petrasek",
    19: "Melwin Pantzar",      20: "Amar Sylla",
    22: "Aleix Font",          32: "Tryggvi Hlinason",
    73: "Stefan Lazarevic",
}
```

---

## 🌿 Flujo de ramas — OBLIGATORIO

**Nunca trabajar directamente en `master` ni en `develop`.**

```
master    ← producción (Streamlit Cloud). Solo recibe merges desde develop.
develop   ← integración. Solo recibe merges desde feature branches validadas.
feature/  ← una rama por sub-tarea. Se crea desde develop, se mergea a develop.
```

```bash
# Para CUALQUIER tarea — siempre este flujo completo
git checkout develop && git pull origin develop
git checkout -b fix/descripcion-corta     # o feature/, data/, refactor/, test/

# ... trabajar, commitear en pasos pequeños ...

pytest tests/ -v                          # todos verdes → merge; alguno rojo → corregir primero
git checkout develop
git merge fix/descripcion-corta
git push origin develop

# Solo cuando develop esté estable → subir a producción
git checkout master
git merge develop
git push origin master                    # dispara redeploy en Streamlit Cloud
```

| Prefijo | Cuándo usar |
|---------|-------------|
| `feature/` | nueva funcionalidad |
| `fix/` | corrección de bug |
| `data/` | añadir partidos o migración |
| `refactor/` | reestructuración sin cambio de comportamiento |
| `test/` | añadir o mejorar tests |

> Detalle completo en `.claude/rules/git-workflow.md`

---

## 🔍 Análisis de sesiones Claude Code

Los logs de sesión están en `~/.claude/projects/`. Usarlos cuando:
- Una tarea consume demasiados tokens sin completarse
- Un subagente parece ir fuera de contexto o repite trabajo
- Quieres entender por qué un workflow no se completó

```bash
# Ver sesiones del proyecto
ls ~/.claude/projects/-home-leandro-Documentos-projects-acb/

# Pedir a Claude Code que analice la sesión problemática
# "Analiza la sesión [nombre/id], identifica dónde se desperdiciaron tokens
#  y qué se puede cambiar en las skills o CLAUDE.md para evitarlo"
```

> Skill de análisis en `.claude/skills/session-analysis/SKILL.md`

---

## 🐛 Bugs activos

| Bug | Prioridad | Rama sugerida |
|-----|-----------|---------------|
| Jugadores rivales en análisis Bilbao | 🔴 CRÍTICO | `fix/bilbao-player-isolation` |
| Jornadas siempre `J1` | 🟡 media | `fix/season-trends-jornadas` |
| Abreviaturas rivales truncadas | 🟡 media | `fix/rival-abbreviations` |
| Botón "Actualizar datos" visible en cloud | 🟡 media | `fix/hide-update-button-cloud` |
| `rebuild_lineups` falla en cloud | 🟡 media | `fix/lineups-cloud-separation` |
