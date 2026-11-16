"""Orquesta el pipeline completo: esquema -> carga -> transformación.

Uso:
    python -m src.etl.pipeline --json data/raw/games.json --snapshot-date 2026-01-15
    python -m src.etl.pipeline --skip-load      # solo recrea esquema y transforma
"""
import argparse
from datetime import date
from pathlib import Path

from src.etl.db import ROOT, connect, run_sql_file
from src.etl.load_kaggle import load

SQL_DIR = ROOT / "sql"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="Ruta al games.json de FronkonGames")
    parser.add_argument("--snapshot-date", type=date.fromisoformat)
    parser.add_argument("--skip-load", action="store_true")
    args = parser.parse_args()

    with connect() as conn:
        print("1/3 Creando esquema...")
        run_sql_file(conn, SQL_DIR / "01_schema.sql")

    if not args.skip_load:
        if not (args.json and args.snapshot_date):
            parser.error("--json y --snapshot-date son obligatorios si no usas --skip-load")
        print("2/3 Cargando JSON en staging...")
        load(args.json, args.snapshot_date)
    else:
        print("2/3 Carga omitida")

    with connect() as conn:
        print("3/3 Transformando a modelo estrella...")
        run_sql_file(conn, SQL_DIR / "02_transform.sql")
        counts = conn.execute("""
            SELECT (SELECT count(*) FROM core.dim_game),
                   (SELECT count(*) FROM core.fact_game_snapshot),
                   (SELECT count(*) FROM core.dim_tag),
                   (SELECT count(*) FROM core.dim_game WHERE release_date IS NULL)
        """).fetchone()
    print(f"Juegos: {counts[0]:,} | Snapshots: {counts[1]:,} | "
          f"Tags: {counts[2]:,} | Sin fecha válida: {counts[3]:,}")


if __name__ == "__main__":
    main()
