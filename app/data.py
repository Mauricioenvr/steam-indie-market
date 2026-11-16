"""Carga del extracto y cálculo de métricas para el dashboard."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "dashboard"

DAYS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes",
        6: "Sábado", 7: "Domingo"}
MONTHS = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul",
          8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
REVIEWS_GOAL = 100      # umbral de "alcance" usado en todo el proyecto
MIN_REVIEWS_RATING = 50  # mínimo de reseñas para que el % positivo sea estable


@st.cache_data
def load():
    games = pd.read_parquet(DATA_DIR / "games.parquet")
    tags = pd.read_parquet(DATA_DIR / "game_tags.parquet")
    genres = pd.read_parquet(DATA_DIR / "game_genres.parquet")
    meta = json.loads((DATA_DIR / "meta.json").read_text(encoding="utf-8"))
    games["llega_100"] = games["total_reviews"] >= REVIEWS_GOAL
    games["tiene_tags"] = games["app_id"].isin(tags["app_id"])
    games["tramo"] = games["tramo_precio"].astype(str).str.split(". ", n=1).str[1]
    return games, tags, genres, meta


def years(meta: dict) -> dict:
    """Años de referencia según la fecha del snapshot."""
    s = int(meta["snapshot_date"][:4])
    return {
        "ultimo_completo": s - 1,   # último año con lanzamientos completos
        "ultimo_maduro": s - 2,     # último año cuyos juegos ya acumularon reseñas
        "ultimo_cohorte": s - 3,    # fin de las cohortes usadas en los modelos
    }


def summary(df: pd.DataFrame) -> dict:
    """Métricas de alcance y calidad de un grupo de juegos."""
    rated = df.loc[df["total_reviews"] >= MIN_REVIEWS_RATING, "pct_positive"]
    return {
        "n": len(df),
        "pct_100": 100 * df["llega_100"].mean() if len(df) else float("nan"),
        "mediana_resenas": df["total_reviews"].median() if len(df) else float("nan"),
        "valoracion": rated.median() if len(rated) else float("nan"),
        "n_valorados": len(rated),
    }


def by_group(df: pd.DataFrame, col: str, order=None, labels=None) -> pd.DataFrame:
    """Lanzamientos, % que llega a 100 reseñas y valoración mediana por grupo."""
    out = (df.groupby(col, observed=True)
             .agg(juegos=("app_id", "size"),
                  pct_100=("llega_100", "mean"))
             .assign(pct_100=lambda d: 100 * d["pct_100"],
                     pct_juegos=lambda d: 100 * d["juegos"] / d["juegos"].sum()))
    rated = (df[df["total_reviews"] >= MIN_REVIEWS_RATING]
             .groupby(col, observed=True)["pct_positive"].median().rename("valoracion"))
    out = out.join(rated)
    if order is not None:
        out = out.reindex(order)
    out = out.reset_index()
    if labels is not None:
        out["etiqueta"] = out[col].map(labels)
    else:
        out["etiqueta"] = out[col].astype(str)
    return out


def concentration(df: pd.DataFrame) -> pd.DataFrame:
    """Parte de todas las reseñas que acumula cada grupo de juegos."""
    r = df["total_reviews"].sort_values(ascending=False).to_numpy()
    n, total = len(r), r.sum()
    cuts = [("1 % más reseñado", 0, 0.01), ("Siguiente 9 %", 0.01, 0.10),
            ("Siguiente 40 %", 0.10, 0.50), ("50 % menos reseñado", 0.50, 1.0)]
    rows = [(name, 100 * r[int(a * n):int(b * n)].sum() / total) for name, a, b in cuts]
    return pd.DataFrame(rows, columns=["grupo", "pct_resenas"])
