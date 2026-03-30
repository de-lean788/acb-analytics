# deploy.md

Deploy a Streamlit Cloud:

1. **Tests primero** — no hay excepciones:
   ```bash
   pytest tests/ -v
   ```

2. **Migrar BD si hay partidos nuevos**:
   ```bash
   python migrate_to_supabase.py --target $(cat .env | grep SUPABASE_URL | cut -d= -f2)
   ```

3. **Push** — el deploy es automático tras push a `master`:
   ```bash
   git add <ficheros>
   git commit -m "tipo: descripción"
   git push origin master
   ```

4. **Verificar** en `acb-analytics-bilbao.streamlit.app`:
   - ¿Carga sin error?
   - ¿Los jugadores en On/Off son todos de Bilbao? (no rivales)
   - ¿Los gráficos de temporada muestran jornadas correctas?

5. **Si falla**: revisar logs en Streamlit Cloud > App > Logs.
   Errores frecuentes:
   - `operator does not exist: boolean = integer` → `is_bilbao = TRUE` no `= 1`
   - `UndefinedColumn` → `GROUP BY` incompleto en PostgreSQL
   - `connection refused` → Supabase pausado (plan gratuito, 7 días sin actividad)
