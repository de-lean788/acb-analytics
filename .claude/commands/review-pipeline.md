# review-pipeline.md

Revisa el pipeline de datos de este fichero o función:

- Errores lógicos (especialmente is_bilbao home/away)
- ¿Usa MAX() o SUM() para stats acumulativas?
- ¿Maneja correctamente el caso de Bilbao como visitante?
- ¿Hay logging en cada paso?
- ¿Está testeado?
- Performance: ¿hay N+1 queries o loops innecesarios?
- Edge cases: partidos con prórroga, jugadores sin minutos, CSVs vacíos
