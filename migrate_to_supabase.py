"""
Migración SQLite → Supabase (PostgreSQL)
==========================================
Copia todos los datos de la BD local a Supabase.

Uso:
    python scripts/migrate_to_supabase.py --target "postgresql+psycopg2://..."

El argumento --target acepta la URL de conexión de Supabase.
La encontrarás en: Supabase → Project → Settings → Database → Connection string (URI)
Cambia [YOUR-PASSWORD] por tu contraseña real.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.models import Base, Match, Player, Event, Lineup, get_engine, create_tables


def migrate(source_url: str, target_url: str, batch_size: int = 500):
    print(f"\nOrigen : {source_url}")
    print(f"Destino: {target_url[:40]}...\n")

    src = get_engine(source_url)
    tgt = get_engine(target_url)

    # Crear tablas en destino
    print("Creando tablas en Supabase...")
    create_tables(tgt)

    with Session(src) as s_src, Session(tgt) as s_tgt:

        # ── Matches ───────────────────────────────────────────────────────────
        matches = s_src.query(Match).all()
        print(f"Migrando {len(matches)} partidos...", end=" ")
        for m in matches:
            if not s_tgt.get(Match, m.id):
                s_tgt.merge(m)
        s_tgt.commit()
        print("✓")

        # ── Players ───────────────────────────────────────────────────────────
        players = s_src.query(Player).all()
        print(f"Migrando {len(players)} jugadores...", end=" ")
        for p in players:
            if not s_tgt.get(Player, p.id):
                s_tgt.merge(p)
        s_tgt.commit()
        print("✓")

        # ── Events (en batches) ───────────────────────────────────────────────
        total_events = s_src.query(Event).count()
        print(f"Migrando {total_events} eventos en batches de {batch_size}...")
        offset = 0
        while True:
            batch = s_src.query(Event).offset(offset).limit(batch_size).all()
            if not batch:
                break
            for e in batch:
                s_tgt.merge(e)
            s_tgt.commit()
            offset += batch_size
            pct = min(100, int(offset / total_events * 100))
            print(f"  {pct}% ({min(offset, total_events)}/{total_events})")
        print("  Eventos ✓")

        # ── Lineups ───────────────────────────────────────────────────────────
        lineups = s_src.query(Lineup).all()
        print(f"Migrando {len(lineups)} stints de lineups...", end=" ")
        for l in lineups:
            s_tgt.merge(l)
        s_tgt.commit()
        print("✓")

    # Verificación final
    print("\nVerificando...")
    with Session(tgt) as s:
        print(f"  Partidos : {s.query(Match).count()}")
        print(f"  Jugadores: {s.query(Player).count()}")
        print(f"  Eventos  : {s.query(Event).count()}")
        print(f"  Lineups  : {s.query(Lineup).count()}")

    print("\n✅ Migración completada.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migración SQLite → Supabase")
    parser.add_argument(
        "--source",
        default="sqlite:///./data/db/bilbao.db",
        help="URL BD origen (default: SQLite local)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="URL BD destino (Supabase connection string)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Tamaño de batch para eventos (default: 500)",
    )
    args = parser.parse_args()
    migrate(args.source, args.target, args.batch_size)
