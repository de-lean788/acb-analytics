---
name: analyzing-basketball-data
description: >
  Usar cuando se implementan o modifican métricas, cálculos de lineup, On/Off splits,
  o cualquier análisis estadístico (analytics/metrics.py, analytics/lineups.py).
---

## Workflow

```
1. Cargar datos filtrados correctamente (Bilbao vs rival)
2. Calcular métricas con fórmulas validadas
3. Añadir explicación coach-friendly a cada output
4. Contextualizar vs media del equipo / partido anterior
```

## Fórmulas implementadas

### Four Factors (Dean Oliver)

```python
efg_pct   = (fg2m + 1.5 * fg3m) / fga if fga > 0 else 0.0
tov_pct   = tov / (fga + 0.44 * fta + tov) if (fga + 0.44*fta + tov) > 0 else 0.0
oreb_pct  = oreb / (oreb + opp_dreb) if (oreb + opp_dreb) > 0 else 0.0
ftr       = fta / fga if fga > 0 else 0.0
```

### Ratings (por 100 posesiones)

```python
poss = fga - oreb + tov + 0.44 * fta
off_rating = (pts / poss) * 100 if poss > 0 else 0.0
def_rating = (opp_pts / opp_poss) * 100 if opp_poss > 0 else 0.0
net_rating = off_rating - def_rating
```

### True Shooting %

```python
ts_pct = pts / (2 * (fga + 0.44 * fta)) if (fga + 0.44*fta) > 0 else 0.0
```

### On/Off differential

```python
on_off_diff = pts_net_on - pts_net_off
# pts_net_on = puntos netos del equipo mientras el jugador está en pista
```

## Traducción al cuerpo técnico

| Métrica | Explicación coach |
|---------|-------------------|
| `NetRating` | Puntos que gana/pierde el equipo por cada 100 posesiones |
| `eFG%` | Eficiencia real de tiro (el triple vale más que el doble) |
| `TS%` | Eficiencia total incluyendo tiros libres |
| `TOV%` | De cada 100 posesiones, cuántas acaban en pérdida |
| `OREB%` | Del total de rebotes ofensivos disponibles, cuántos captura el equipo |
| `On/Off diff` | Cuánto mejora o empeora el equipo cuando este jugador está en pista |
| `FTR` | Con qué frecuencia el equipo llega a la línea de tiros libres |

## Umbrales de referencia ACB

```python
THRESHOLDS = {
    "efg_pct":   {"good": 0.54, "bad": 0.46},
    "ts_pct":    {"good": 0.57, "bad": 0.50},
    "tov_pct":   {"good": 0.14, "bad": 0.18},  # lower is better
    "net_rating":{"good": 5.0,  "bad": -5.0},
}
```

## Reconstrucción de quintetos (lineups.py)

```python
# play_type 115 → jugador ENTRA a cancha (añadir al quinteto activo)
# play_type 112 → jugador SALE de cancha (retirar del quinteto activo)

active_lineup = set()
for _, row in df.iterrows():
    if row["play_type"] == 115:
        active_lineup.add(row["player_name"])
    elif row["play_type"] == 112:
        active_lineup.discard(row["player_name"])
```

## Reference

- `analytics/metrics.py` — implementación actual
- `analytics/lineups.py` — reconstrucción de quintetos
- `.claude/rules/data-quality.md` — validaciones obligatorias
