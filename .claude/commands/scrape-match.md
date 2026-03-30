# scrape-match.md

Scrapea un partido de la API ACB:

1. Obtén el `match_id` de la URL de acb.com (ej: `/partido/ver/id/104481`)
2. Asegúrate de tener `ACB_API_KEY` en `.env`
3. Ejecuta:
   ```bash
   python acb_scraper.py --match-id <ID>
   ```
4. Verifica que el CSV generado sigue el naming correcto:
   `YYYYMMDD_<matchId>_<Local>_vs_<Away>_plays.csv`
5. Comprueba que el CSV tiene eventos de ambos equipos (columna `team_role`: home y away)
6. Si hay error 401/403: obtener nueva `X-APIKEY` desde DevTools del navegador en acb.com

Para scraping masivo (varios partidos):
```bash
# Con pausa entre requests — no más de 5 seguidos sin revisar
for id in 104481 104492 104495 104511; do
    python acb_scraper.py --match-id $id
    sleep 2
done
```
