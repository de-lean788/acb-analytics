---
name: analyzing-claude-sessions
description: >
  Usar cuando una tarea consume demasiados tokens, un subagente va fuera de contexto,
  un workflow no se completa, o quieres optimizar el uso de tokens en Claude Code.
---

## Dónde están los logs

```bash
# Linux/Mac
~/.claude/projects/

# El proyecto acb-analytics específicamente
~/.claude/projects/-home-leandro-Documentos-projects-acb/

# Dentro hay un .jsonl por sesión — uno por cada vez que arrancaste claude
ls ~/.claude/projects/-home-leandro-Documentos-projects-acb/*.jsonl
```

Cada fichero `.jsonl` es un log completo: prompts, respuestas, tool calls, tokens usados.

## Cuándo analizar una sesión

- La tarea no se completó y no sabes por qué
- Claude parece repetir trabajo o leer los mismos ficheros varias veces
- Te quedaste sin tokens antes de terminar
- Un subagente hizo algo inesperado o fue "off-script"
- Quieres entender cuántos tokens consume una skill concreta

## Workflow de análisis

### Paso 1 — Nombrar la sesión antes de que acabe (en Claude Code)
```
/rename fix-bilbao-player-isolation-session
```
Facilita encontrarla después.

### Paso 2 — Abrir una sesión nueva para el análisis
No analices la sesión problemática dentro de ella misma.

### Paso 3 — Cargar y analizar el log
```bash
# Ver las últimas sesiones
ls -lt ~/.claude/projects/-home-leandro-Documentos-projects-acb/*.jsonl | head -5

# Contar tokens aproximados por sesión
cat <session.jsonl> | python3 -c "
import sys, json
total = 0
for line in sys.stdin:
    try:
        obj = json.loads(line)
        # buscar campos de tokens en distintos formatos
        for key in ['input_tokens', 'output_tokens', 'tokens']:
            if key in obj:
                total += obj[key]
    except: pass
print(f'Tokens aproximados: {total}')
"
```

### Paso 4 — Pedir análisis a Claude Code
```
"Analiza el log de sesión en [ruta]. Identifica:
1. Qué pasos consumieron más tokens
2. Si algún subagente leyó ficheros innecesariamente
3. Si hay contexto que se pasó completo cuando solo se necesitaba un resumen
4. Qué cambios en CLAUDE.md o en las skills reducirían el uso de tokens
sin perder calidad"
```

### Paso 5 — Aplicar los cambios
Si Claude identifica waste en una skill → editar esa skill.
Si el waste es en CLAUDE.md → reducir contexto innecesario.
Siempre testear con una tarea real tras el cambio.

## Patrones comunes de waste en este proyecto

| Síntoma | Causa probable | Fix |
|---------|---------------|-----|
| Sesión agotada antes de terminar | Subagente pasa contexto completo al agente principal | Reducir output del subagente a solo el resultado, no el proceso |
| Claude relee el mismo fichero varias veces | Falta de instrucción "no releer si ya está en contexto" | Añadir a la skill relevante |
| Claude genera más código del pedido | Scope de la tarea demasiado abierto | Ser más específico en el command/prompt |
| Análisis de datos lento | Carga todo el CSV en lugar de muestra | Instruir a usar `df.head(100)` para exploración |

## Principio general

**Blaming processes, not models.** Si Claude desperdicia tokens, casi siempre es un problema
de cómo están escritas las instrucciones — skills, rules, o el prompt inicial.
Analizar la sesión lo hace visible y solucionable.
