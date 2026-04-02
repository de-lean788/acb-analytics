---
name: analyzing-claude-sessions
description: >
  Usar cuando una tarea no se completó, un subagente fue fuera de contexto,
  se agotaron tokens antes de terminar, o quieres entender qué causó el problema.
---

## Dónde están los logs
```bash
ls ~/.claude/projects/-home-leandro-Documentos-projects-acb/*.jsonl
```
Cada `.jsonl` es un log completo: prompts, respuestas, tool calls, tokens usados.

## Cuándo usar este skill
- La sesión se agotó antes de completar la tarea
- Claude repitió lecturas de ficheros o pareció perder contexto
- Un subagente hizo algo inesperado
- Quieres saber qué skill o paso consumió más tokens

## Workflow

### Paso 1 — Nombrar la sesión antes de que acabe
```
/rename descripcion-corta-de-la-tarea
```

### Paso 2 — Abrir sesión nueva para el análisis
No analices la sesión problemática dentro de ella misma.

### Paso 3 — Identificar la sesión
```bash
ls -lt ~/.claude/projects/-home-leandro-Documentos-projects-acb/*.jsonl | head -5
```

### Paso 4 — Analizar tokens por sesión
```bash
cat <session.jsonl> | python3 -c "
import sys, json
total = 0
for line in sys.stdin:
    try:
        obj = json.loads(line)
        for key in ['input_tokens', 'output_tokens', 'tokens']:
            if key in obj:
                total += obj[key]
    except: pass
print(f'Tokens aproximados: {total}')
"
```

### Paso 5 — Pedir análisis a Claude Code
```
"Analiza el log en [ruta]. Identifica:
1. Qué pasos consumieron más tokens
2. Si algún subagente leyó ficheros innecesariamente o pasó contexto completo
3. Si se cargaron CSVs enteros en lugar de muestras
4. Qué cambio concreto en qué skill o rule reduciría el problema"
```

### Paso 6 — Aplicar el fix
- Waste en una skill → editar esa skill (añadir sección `## Token efficiency`)
- Waste en contexto general → reducir o mover contenido de `CLAUDE.md`
- Comportamiento repetitivo → añadir instrucción explícita en la rule relevante

## Patrones comunes en este proyecto

| Síntoma | Causa probable | Fix |
|---------|---------------|-----|
| Sesión agotada antes de terminar | Subagente devuelve proceso completo, no solo resultado | Añadir "devuelve solo el resultado final" en la skill del subagente |
| Claude relee el mismo fichero | Falta instrucción explícita de no releer | Añadir a `token-efficiency.md` o a la skill relevante |
| Análisis de datos lento o costoso | Carga CSV completo | Instruir `df.head(100)` en `data-pipeline/SKILL.md` |
| Claude genera más código del pedido | Prompt demasiado abierto | Ser más específico en el command o prompt inicial |
| Subagente va off-script | Spawn prompt demasiado vago | Reducir scope del spawn prompt, una tarea concreta por subagente |

## Principio
Si Claude desperdicia tokens, casi siempre es un problema de instrucciones — skills, rules, o el prompt.
Analizar la sesión lo hace visible y accionable.