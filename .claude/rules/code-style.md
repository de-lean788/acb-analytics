# code-style.md

## Python general

- Python 3.12, type hints en funciones públicas
- Logging estructurado — no usar `print()` en producción
- Docstrings estilo Google en funciones públicas
- Funciones puras siempre que sea posible — evitar side-effects en transformaciones

```python
# ✅
def calculate_efg(fg2m: int, fg3m: int, fga: int) -> float:
    """Calcula eFG% (Effective Field Goal Percentage).
    
    Args:
        fg2m: Canastas de 2 puntos anotadas.
        fg3m: Canastas de 3 puntos anotadas.
        fga: Intentos de campo totales.
    
    Returns:
        eFG% como float entre 0 y 1. Retorna 0.0 si fga == 0.
    """
    if fga == 0:
        return 0.0
    return (fg2m + 1.5 * fg3m) / fga
```

## pandas

- Operaciones vectorizadas — nunca `iterrows()`
- Especificar `dtype` en `read_csv()` para columnas críticas:

```python
df = pd.read_csv(path, dtype={
    "is_local": bool,
    "play_type": int,
    "quarter": int,
})
```

## SQLAlchemy / SQL

- ORM para operaciones CRUD estándar
- SQL raw solo para queries analíticas complejas
- Queries parametrizadas — nunca f-strings con input de usuario
- PostgreSQL: `chunksize=100` en `to_sql()` — no `method="multi"`
- Booleanos: `TRUE/FALSE` en SQL, nunca `0/1`
- `GROUP BY` completo — PostgreSQL es más estricto que SQLite

## Git

```
fix:      corrección de bug
feat:     nueva funcionalidad
refactor: reestructuración sin cambio de comportamiento
test:     añadir o corregir tests
data:     cambios en datos o migración
```
