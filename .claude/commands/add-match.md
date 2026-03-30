# add-match.md

Añade un partido nuevo al sistema end-to-end:

1. Verifica que el CSV sigue el naming: `YYYYMMDD_matchId_LocalTeam_vs_AwayTeam_plays.csv`
2. Cópialo a `data/csv/`
3. Ejecuta `python -m pipeline.ingest --dir data/csv` y verifica que no hay errores
4. Comprueba que los jugadores del partido nuevo son reconocidos como Bilbao o rival correctamente:
   ```python
   python -c "
   from analytics.validators import validate_bilbao_players
   # mostrar qué jugadores se detectaron como Bilbao en el nuevo match_id
   "
   ```
5. Ejecuta `pytest tests/ -v` — todos deben pasar
6. Si el deploy es cloud: ejecuta `python migrate_to_supabase.py`
7. Push: `git add data/ && git commit -m "data: añadir partido [rival] [fecha]" && git push`
