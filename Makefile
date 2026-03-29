.PHONY: setup ingest ingest-reset test db-shell

# ── Setup ──────────────────────────────────────────────────────────────────────
setup:
	python -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	mkdir -p data/db data/csv
	cp .env.example .env
	@echo "✓ Entorno listo. Copia tus CSVs en data/csv/ y ejecuta 'make ingest'"

# ── Ingesta ────────────────────────────────────────────────────────────────────
ingest:
	python -m pipeline.ingest --dir data/csv

ingest-reset:
	python -m pipeline.ingest --dir data/csv --reset

ingest-file:
	@[ "$(FILE)" ] || (echo "Uso: make ingest-file FILE=data/csv/tu_fichero.csv" && exit 1)
	python -m pipeline.ingest --file $(FILE)

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

# ── DB ─────────────────────────────────────────────────────────────────────────
db-shell:
	sqlite3 data/db/bilbao.db

db-check:
	sqlite3 data/db/bilbao.db ".tables" && \
	sqlite3 data/db/bilbao.db "SELECT COUNT(*) as partidos FROM matches;" && \
	sqlite3 data/db/bilbao.db "SELECT COUNT(*) as eventos FROM events;" && \
	sqlite3 data/db/bilbao.db "SELECT COUNT(*) as jugadores FROM players;"

# ── Dashboard ──────────────────────────────────────────────────────────────────
dashboard:
	streamlit run dashboard/app.py

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up -d
	@echo "Adminer disponible en http://localhost:8080"

docker-down:
	docker compose down

docker-ingest:
	docker compose exec analytics python -m pipeline.ingest --dir data/csv
