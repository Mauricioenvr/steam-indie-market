"""Exporta un extracto ligero de PostgreSQL para el dashboard (data/dashboard/).

El dashboard publicado no tiene acceso a la base de datos: lee estos archivos.
Vuelve a ejecutarlo cada vez que cargues un snapshot nuevo.

Uso:
    python -m src.etl.export_dashboard
"""
import json

import pandas as pd

from src.etl.db import ROOT, connect

OUT_DIR = ROOT / "data" / "dashboard"

# Indies publicados (sin software), desde 2014: el año en que se abrió la tienda
GAMES_SQL = """
    SELECT g.app_id, g.name, g.release_date,
           extract(year FROM g.release_date)::smallint      AS anio,
           extract(month FROM g.release_date)::smallint     AS mes,
           CASE WHEN g.release_date_raw ~ '^[A-Za-z]{3,9} \\d{4}$' THEN NULL
                ELSE extract(isodow FROM g.release_date)::smallint END AS dia_semana,
           g.tramo_precio, g.list_price_usd, g.total_reviews, g.pct_positive,
           g.is_early_access
    FROM core.v_game_latest g
    WHERE g.is_indie AND g.release_date >= '2014-01-01'
"""
TAGS_SQL = """
    SELECT bt.app_id, t.name AS tag
    FROM core.bridge_game_tag bt
    JOIN core.dim_tag t USING (tag_id)
    WHERE bt.tag_rank <= 5 AND t.name <> 'Indie'
      AND bt.app_id = ANY(%s)
"""
GENRES_SQL = """
    SELECT bg.app_id, ge.name AS genero
    FROM core.bridge_game_genre bg
    JOIN core.dim_genre ge USING (genre_id)
    WHERE ge.name NOT IN ('Indie', 'Early Access') AND bg.app_id = ANY(%s)
"""


def _query(cur, sql, params=None) -> pd.DataFrame:
    cur.execute(sql, params)
    return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn, conn.cursor() as cur:
        games = _query(cur, GAMES_SQL)
        ids = games["app_id"].tolist()
        tags = _query(cur, TAGS_SQL, (ids,))
        genres = _query(cur, GENRES_SQL, (ids,))
        snapshot = cur.execute("SELECT max(snapshot_date) FROM core.fact_game_snapshot").fetchone()[0]

    # Tipos compactos: el extracto se versiona en el repo
    games["release_date"] = pd.to_datetime(games["release_date"])
    games["list_price_usd"] = pd.to_numeric(games["list_price_usd"]).astype("float32")
    games["pct_positive"] = pd.to_numeric(games["pct_positive"]).astype("float32")
    games["total_reviews"] = games["total_reviews"].astype("int32")
    games["dia_semana"] = games["dia_semana"].astype("Int8")
    games["tramo_precio"] = games["tramo_precio"].astype("category")
    tags["tag"] = tags["tag"].astype("category")
    genres["genero"] = genres["genero"].astype("category")

    games.to_parquet(OUT_DIR / "games.parquet", index=False)
    tags.to_parquet(OUT_DIR / "game_tags.parquet", index=False)
    genres.to_parquet(OUT_DIR / "game_genres.parquet", index=False)
    (OUT_DIR / "meta.json").write_text(json.dumps({
        "snapshot_date": snapshot.isoformat(),
        "fuente": "FronkonGames Steam Games Dataset (Kaggle)",
        "juegos": len(games),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    size_mb = sum(f.stat().st_size for f in OUT_DIR.glob("*")) / 1e6
    print(f"{len(games):,} juegos | {len(tags):,} tags | {len(genres):,} géneros | "
          f"{size_mb:.1f} MB en {OUT_DIR}")


if __name__ == "__main__":
    main()
