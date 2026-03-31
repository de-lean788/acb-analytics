"""
pipeline/set_round_numbers.py
==============================
Migración: añade la columna round_number a la tabla matches (si no existe)
y la rellena desde data/acb_calendar_2526.json.

Uso:
    python -m pipeline.set_round_numbers           # usa la BD por defecto
    python -m pipeline.set_round_numbers --dry-run # muestra cambios sin aplicar
"""

import json
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import get_engine


def run(dry_run: bool = False) -> None:
    cal_path = Path(__file__).parent.parent / "data" / "acb_calendar_2526.json"
    if not cal_path.exists():
        print(f"ERROR: No se encontró {cal_path}")
        sys.exit(1)

    with open(cal_path) as f:
        data = json.load(f)

    round_map: dict[int, int] = {
        e["match_id"]: e["jornada"]
        for e in data.get("jornadas", [])
        if e.get("match_id") and e.get("jornada")
    }

    engine = get_engine()

    with engine.connect() as conn:
        # 1. Añadir columna si no existe (SQLite y PostgreSQL)
        try:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(matches)"))]
            is_sqlite = True
        except Exception:
            is_sqlite = False
            cols = [row[0] for row in conn.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_name='matches'")
            )]

        if "round_number" not in cols:
            if dry_run:
                print("DRY-RUN: ALTER TABLE matches ADD COLUMN round_number INTEGER")
            else:
                conn.execute(text("ALTER TABLE matches ADD COLUMN round_number INTEGER"))
                conn.commit()
                print("Columna round_number añadida a matches.")
        else:
            print("Columna round_number ya existe.")

        # 2. Obtener partidos actuales
        matches = conn.execute(text("SELECT id FROM matches")).fetchall()
        match_ids = [r[0] for r in matches]

        updated = 0
        not_found = []
        for mid in match_ids:
            jornada = round_map.get(mid)
            if jornada:
                if dry_run:
                    print(f"  DRY-RUN: match {mid} → J{jornada}")
                else:
                    conn.execute(
                        text("UPDATE matches SET round_number = :j WHERE id = :id"),
                        {"j": jornada, "id": mid},
                    )
                updated += 1
            else:
                not_found.append(mid)

        if not dry_run:
            conn.commit()

    print(f"\nActualizados: {updated} partidos")
    if not_found:
        print(f"Sin jornada en calendario: match_ids {not_found}")
        print("  → Añade esos partidos a data/acb_calendar_2526.json y reejcuta.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
