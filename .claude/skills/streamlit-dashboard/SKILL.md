---
name: building-streamlit-dashboard
description: >
  Usar en cambios a dashboard/ o cualquier vista del proyecto.
  Cubre estructura de vistas, cacheo, detección cloud/local y patrones visuales.
---

## Workflow

```
1. Separar capa de datos (analytics/) de capa de presentación (dashboard/)
2. Cachear todas las queries
3. Validar datos antes de renderizar
4. Usar helpers visuales del proyecto (base_layout, hex_to_rgba)
5. Detectar entorno cloud vs local
```

## Estructura estándar de vista

```python
# dashboard/views/mi_vista.py
import streamlit as st
import pandas as pd
from analytics.metrics import get_mi_metrica

def render() -> None:
    st.title("Título de la vista")
    df = _load_data()
    if df.empty:
        st.warning("No hay datos disponibles.")
        return
    _render_main(df)

@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Carga datos desde analytics/. Cache de 5 min."""
    return get_mi_metrica()

def _render_main(df: pd.DataFrame) -> None:
    tab1, tab2 = st.tabs(["Vista A", "Vista B"])
    with tab1:
        _render_tab_a(df)    # return si vacío, NUNCA st.stop()
    with tab2:
        _render_tab_b(df)
```

## Helpers visuales del proyecto

```python
from dashboard.utils import base_layout, hex_to_rgba

# Layout consistente — has_legend=True añade margen superior
fig.update_layout(base_layout(has_legend=True))

# fillcolor en Scatterpolar — siempre hex_to_rgba, nunca concatenar
fillcolor = hex_to_rgba("#FFE000", alpha=0.3)
```

## Tema visual

```python
BILBAO_YELLOW = "#FFE000"
BACKGROUND    = "#1a1a1a"
# Fuentes: Syne (títulos), DM Mono (datos)
```

## Detección cloud vs local

```python
IS_CLOUD = "database" in st.secrets

# Botón de actualización — solo en local
if not IS_CLOUD:
    if st.button("🔄 Actualizar datos"):
        with st.spinner("Procesando..."):
            rebuild_lineups()
```

## Vistas actuales

| Vista | Fichero | Estado |
|-------|---------|--------|
| Impacto de Jugadores | `player_impact.py` | ✅ |
| Tendencia de Temporada | `season_trends.py` | 🟡 J1 hardcoded |
| Último Partido | `last_match.py` | ✅ |
| Análisis de Rival | `rival_analysis.py` | ✅ |

## Reference

- `dashboard/app.py` — entry point
- `dashboard/views/` — vistas actuales
- `.claude/rules/streamlit.md` — reglas detalladas

## Token efficiency
- Para depurar una vista: trabajar con datos mockeados o `df.head(20)`, no datos reales completos
- No leer `app.py` salvo que el problema sea de routing — las vistas son independientes
- Al modificar una vista: leer solo ese fichero (`views/mi_vista.py`), no todo `dashboard/`