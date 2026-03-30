# git-workflow.md

Aplicar en CUALQUIER tarea que implique cambios de código o datos.

## La regla de oro

```
master   → producción. SOLO recibe merges desde develop. Nunca tocar directamente.
develop  → integración. SOLO recibe merges desde branches validadas con tests verdes.
feature/ → trabajo real. Una rama por sub-tarea. Se crea desde develop.
```

## Flujo completo — seguirlo siempre, sin excepciones

```bash
# 1. Partir desde develop actualizado
git checkout develop
git pull origin develop

# 2. Crear rama con nombre descriptivo
git checkout -b fix/bilbao-player-isolation
#              ↑ prefijo  ↑ descripción-en-kebab-case

# 3. Trabajar en pasos pequeños y commiteables
git add analytics/lineups.py
git commit -m "fix: usar is_bilbao_home() para inferir home/away desde filename"

git add tests/test_validators.py
git commit -m "test: añadir test_bilbao_flag_away_filtra_correctamente"

# 4. Validar ANTES de mergear — si falla algún test, corregir aquí
pytest tests/ -v
# ✅ todos verdes → continuar
# ❌ alguno rojo  → corregir en esta misma rama, no mergear

# 5. Mergear a develop
git checkout develop
git merge fix/bilbao-player-isolation
git push origin develop
git branch -d fix/bilbao-player-isolation   # limpiar rama local

# 6. Subir a master (producción) — solo cuando develop esté estable
git checkout master
git merge develop
git push origin master    # ← Streamlit Cloud redespliega automáticamente
```

## Nombrado de ramas

| Prefijo | Ejemplo |
|---------|---------|
| `fix/` | `fix/bilbao-player-isolation` |
| `feature/` | `feature/win-probability-chart` |
| `data/` | `data/add-matches-j8-j12` |
| `refactor/` | `refactor/metrics-module-split` |
| `test/` | `test/validators-coverage` |

## Commits — formato

```
tipo: descripción corta en presente (max 72 chars)

fix:      corrección de bug
feat:     nueva funcionalidad
test:     añadir o corregir tests
data:     datos nuevos o migración
refactor: sin cambio de comportamiento
chore:    dependencias, config, CI
```

Ejemplos buenos:
```
fix: usar is_bilbao_home() para inferir home/away desde filename
feat: añadir gráfico de tendencia de jornadas en season_trends
test: cubrir caso Bilbao visitante en test_bilbao_flag
data: añadir partidos J8 a J12 y migrar a Supabase
```

## Reglas adicionales

- Un commit = un cambio lógico. No acumular 10 ficheros en un commit "varios fixes".
- Si un test falla en develop: crear rama `fix/` inmediatamente, no parchear en develop.
- Si tienes dudas de si algo está listo para develop: no lo está. Más tests primero.

## 🤖 Reglas para Claude Code (OBLIGATORIO)

Estas reglas aplican cuando Claude genera o modifica código.

### Gestión de ramas

- NUNCA trabajar directamente en `develop` ni en `master`
- SIEMPRE crear una nueva rama desde `develop`
- El nombre debe seguir el formato definido (`fix/`, `feature/`, etc.)
- Si la tarea implica varios cambios → dividir en varias ramas

### Commits

- Claude debe hacer commits pequeños y atómicos
- Cada commit debe seguir el formato definido
- NO agrupar cambios no relacionados en un mismo commit

### Validación obligatoria

Antes de cualquier merge:

- Ejecutar tests:
  ```bash
  pytest tests/ -v
  ```
Si algún test falla:
- DETENER el proceso
- NO mergear
- Corregir en la misma rama

#### Merges
- Claude NO debe hacer merge directo a master
- Claude NO debe hacer push directo a develop sin validación previa
- El flujo correcto es:
  - crear rama
  - implementar
  - testear
  - merge a develop

#### Pull Requests (si aplica)
- Crear PR claro y descriptivo
- Incluir:
  - qué cambia
  - por qué
  - impacto en datos o métricas

#### Seguridad
- NO sobrescribir datos existentes sin validación
- NO eliminar código sin justificación clara
- NO hacer refactors grandes sin tests

#### Regla de parada

Claude debe PARAR y pedir confirmación si:

- los tests fallan
- hay ambigüedad en la tarea
- el cambio afecta múltiples módulos críticos

---

# 🧠 POR QUÉ ESTO ES CLAVE

Sin esto, Claude tiende a:

❌ modificar `develop` directamente  
❌ hacer commits gigantes  
❌ no ejecutar tests  
❌ romper flujo sin darse cuenta  

Con esto:

✅ debes comportarte como un dev senior  
✅ respetar el pipeline  
✅ reduce errores reales  


### Integración con datos

- Cualquier cambio en datos debe:
  - ser reproducible
  - documentarse
  - versionarse si aplica