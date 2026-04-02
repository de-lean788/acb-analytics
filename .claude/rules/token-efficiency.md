# token-efficiency.md
Aplicar en toda sesión de Claude Code.

## Contexto
- No releer ficheros que ya están en contexto
- No cargar CSVs completos para exploración — usar `df.head(100)`
- No ejecutar comandos con output masivo (`git log`, `pytest -v` completo) salvo que sea necesario

## Sesión
- Una sesión = una tarea lógica (un bug, una feature, un análisis)
- Usar `/compact` en estos momentos:
  - Tras explorar el código y antes de implementar
  - Tras terminar una feature y antes de empezar otra
  - Al llegar a un callejón sin salida, antes de replantear
- Usar `/clear` al cambiar de tarea completamente

## Prompts
- Ser específico: "añade error handling en `pipeline/ingest.py` función `load_csv`" en lugar de "mejora el pipeline"
- Agrupar cambios relacionados en un solo prompt cuando sea posible

## Subagentes
- El output de un subagente debe ser solo el resultado, no el proceso
- Si un subagente analiza datos → devolver solo el resumen, no el DataFrame completo