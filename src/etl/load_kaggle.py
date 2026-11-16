"""Carga el games.json de FronkonGames en staging.games_raw.

El archivo pesa cientos de MB, así que se lee en streaming con ijson
(juego por juego) en vez de cargarlo completo en memoria.

Uso:
    python -m src.etl.load_kaggle data/raw/games.json --snapshot-date 2026-01-15
"""
import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import ijson

from src.etl.db import connect

SOURCE = "kaggle_fronkon"
BATCH_SIZE = 5_000


def _json_default(obj):
    # ijson devuelve los números con decimales como Decimal
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)}")


def iter_games(path: Path):
    """Genera pares (app_id, juego) desde un JSON del tipo {"appid": {...}, ...}."""
    with path.open("rb") as f:
        for app_id, game in ijson.kvitems(f, ""):
            yield int(app_id), game


def load(path: Path, snapshot_date: date, source: str = SOURCE) -> int:
    with connect() as conn, conn.cursor() as cur:
        # Recargar el mismo snapshot reemplaza los datos anteriores
        cur.execute(
            "DELETE FROM staging.games_raw WHERE source = %s AND snapshot_date = %s",
            (source, snapshot_date),
        )
        total = 0
        with cur.copy(
            "COPY staging.games_raw (app_id, source, snapshot_date, payload) FROM STDIN"
        ) as copy:
            for app_id, game in iter_games(path):
                copy.write_row(
                    (app_id, source, snapshot_date,
                     json.dumps(game, default=_json_default, ensure_ascii=False))
                )
                total += 1
                if total % BATCH_SIZE == 0:
                    print(f"  {total:,} juegos cargados...")
        conn.commit()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="Ruta al games.json")
    parser.add_argument("--snapshot-date", type=date.fromisoformat, required=True,
                        help="Fecha de actualización del dataset (YYYY-MM-DD)")
    args = parser.parse_args()

    n = load(args.path, args.snapshot_date)
    print(f"Listo: {n:,} juegos en staging.games_raw")


if __name__ == "__main__":
    main()
