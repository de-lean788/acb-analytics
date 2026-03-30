# data-quality.md

Aplicar en cualquier cambio a `analytics/`, `pipeline/`, `db/`.

## Identificación de jugadores Bilbao

El error más común del proyecto. Bilbao puede ser local O visitante.

```python
# ✅ CORRECTO — inferir del nombre del fichero
def is_bilbao_home(filename: str) -> bool:
    home_team = filename.split("_vs_")[0].split("_", 2)[-1]
    return "SurneBilbao" in home_team

# ❌ NUNCA hardcodear
df[df["is_local"] == True]   # falla cuando Bilbao es visitante
df[df["is_bilbao"] == 1]     # falla en PostgreSQL
```

## Stats acumulativas

Los CSVs son acumulativos dentro del partido. Usar `MAX()`, nunca `SUM()`.

```python
# ✅
df.groupby(["match_id", "player_id"])["pts"].max()

# ❌
df.groupby(["match_id", "player_id"])["pts"].sum()  # duplica valores
```

## Sustituciones — semántica de play_type

```
play_type 115 → "Entra a pista" → jugador ENTRA a cancha
play_type 112 → "Sustitución"   → jugador SALE de cancha
```

Siempre en pares al mismo timestamp. Al reconstruir quintetos: 115 añade, 112 retira.

## Validaciones obligatorias antes de calcular métricas

```python
from analytics.validators import (
    validate_bilbao_players,
    validate_substitution_pairs,
    validate_stats_not_duplicated,
)
# Si alguna falla → lanzar excepción, no continuar con datos incorrectos
```

## Checklist antes de push

- [ ] ¿La lógica de `is_bilbao` tiene en cuenta home/away por partido?
- [ ] ¿Las stats acumulativas usan `MAX()` y no `SUM()`?
- [ ] ¿Existe un test que cubra el cambio?
- [ ] ¿El log muestra qué partidos y jugadores se están procesando?
