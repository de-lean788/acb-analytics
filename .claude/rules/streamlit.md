# streamlit.md

Aplicar en cambios a `dashboard/`.

## Separación de capas (obligatorio)

```python
# ✅ Correcto — datos separados de UI
@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    return get_on_off_splits()   # lógica en analytics/, no aquí

def render():
    df = _load_data()
    if df.empty:
        st.warning("Sin datos disponibles.")
        return                   # return, no st.stop()
    _render_chart(df)

# ❌ No hacer queries dentro de funciones de render
def render():
    df = pd.read_sql("SELECT ...", engine)   # mal
```

## Cache

- `@st.cache_data(ttl=300)` para queries a BD (5 min refresh)
- `@st.cache_data` sin TTL para datos estáticos (roster, config)
- Nunca llamar a BD dentro de loops de render

## Tabs — regla crítica

```python
# ❌ st.stop() dentro de tab mata TODOS los tabs posteriores
with tab1:
    if df.empty:
        st.stop()       # rompe tab2, tab3...

# ✅
with tab1:
    if df.empty:
        st.warning("Sin datos")
        # no renderizar nada más, pero no detener
```

## Detección cloud vs local

```python
IS_CLOUD = "database" in st.secrets

if not IS_CLOUD:
    if st.button("Actualizar datos"):
        ...  # lógica de ingesta solo disponible en local
```

## Visual

- Dark theme configurado en `.streamlit/config.toml`
- Colores: amarillo Bilbao `#FFE000`, fondo `#1a1a1a`
- `base_layout(has_legend=True)` cuando hay leyenda — añade margen superior
- `hex_to_rgba()` para `fillcolor` en Scatterpolar — nunca concatenar strings hex
