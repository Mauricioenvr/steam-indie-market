"""Construye el DataFrame de modelado: variables del juego + géneros + tags de diseño."""
import re

import numpy as np
import pandas as pd

from src.etl.db import ROOT, connect

SQL_PATH = ROOT / "sql" / "analysis" / "model_dataset.sql"

# Géneros declarados por el desarrollador. Se excluyen: 'Indie' (es el universo),
# 'Free To Play' (redundante con el tramo de precio) y 'Early Access'
# (ya es la variable is_early_access).
GENRES = ["Action", "Adventure", "Casual", "RPG", "Simulation", "Strategy",
          "Sports", "Racing", "Massively Multiplayer"]

# Tags de DISEÑO: describen cómo es el juego y el desarrollador los puede decidir.
# Se excluyen los tags de RECEPCIÓN (Great Soundtrack, Memes, Masterpiece,
# Addictive, Beautiful...), porque los jugadores los agregan después de disfrutar
# el juego: son consecuencia del éxito, no causa.
DESIGN_TAGS = [
    "Multiplayer", "Online Co-Op", "Co-op", "Local Co-Op", "PvP",
    "Base-Building", "Management", "Crafting", "Open World", "City Builder",
    "Deckbuilding", "Turn-Based", "Roguelike", "Roguelite", "Survival",
    "Horror", "Visual Novel", "Story Rich", "Choices Matter", "Puzzle",
    "2D Platformer", "Precision Platformer", "Arcade", "Shooter",
    "Pixel Graphics", "Anime", "Female Protagonist", "Sexual Content", "Mature",
]

TAG_RANK_MAX = 5  # igual que en el EDA: los 5 tags que definen al juego


def slug(name: str, prefix: str) -> str:
    """'Online Co-Op' -> 'tag_online_co_op' (nombres válidos para fórmulas)."""
    return prefix + re.sub(r"[^0-9a-z]+", "_", name.lower()).strip("_")


def _query(conn, sql: str, params=None) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def load_model_dataset() -> pd.DataFrame:
    """Devuelve una fila por juego, lista para statsmodels."""
    with connect() as conn:
        base = _query(conn, SQL_PATH.read_text(encoding="utf-8"))
        ids = base["app_id"].tolist()
        genres = _query(conn, """
            SELECT bg.app_id, ge.name
            FROM core.bridge_game_genre bg JOIN core.dim_genre ge USING (genre_id)
            WHERE bg.app_id = ANY(%s) AND ge.name = ANY(%s)""", (ids, GENRES))
        tags = _query(conn, """
            SELECT bt.app_id, t.name
            FROM core.bridge_game_tag bt JOIN core.dim_tag t USING (tag_id)
            WHERE bt.app_id = ANY(%s) AND t.name = ANY(%s) AND bt.tag_rank <= %s""",
            (ids, DESIGN_TAGS, TAG_RANK_MAX))

    df = base.set_index("app_id")

    # Pivotear géneros y tags a columnas 0/1
    for long, names, prefix in [(genres, GENRES, "gen_"), (tags, DESIGN_TAGS, "tag_")]:
        wide = (pd.crosstab(long["app_id"], long["name"]).clip(upper=1)
                if not long.empty else pd.DataFrame(index=df.index))
        for n in names:
            col = slug(n, prefix)
            df[col] = wide[n].reindex(df.index).fillna(0).astype(int) if n in wide else 0

    # Variables numéricas y transformaciones
    num = ["total_reviews", "list_price_usd", "n_languages", "n_audio_languages",
           "achievements", "n_screenshots", "n_movies", "dlc_count"]
    df[num] = df[num].apply(pd.to_numeric).fillna(0)
    df["pct_positive"] = pd.to_numeric(df["pct_positive"])

    df["log_resenas"] = np.log1p(df["total_reviews"])
    df["log_idiomas"] = np.log1p(df["n_languages"])
    df["log_capturas"] = np.log1p(df["n_screenshots"])
    df["tiene_trailer"] = (df["n_movies"] > 0).astype(int)
    df["tiene_logros"] = (df["achievements"] > 0).astype(int)
    df["tiene_dlc"] = (df["dlc_count"] > 0).astype(int)
    df["audio_completo"] = (df["n_audio_languages"] > 0).astype(int)
    for c in ["is_early_access", "mac", "linux", "has_website", "autopublicado", "tiene_tags"]:
        df[c] = df[c].fillna(False).astype(int)

    return df.reset_index()
