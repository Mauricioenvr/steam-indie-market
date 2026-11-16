"""Genera las figuras del README en docs/img/ a partir de la base de datos.

Uso:
    python -m src.analysis.readme_figures
"""
import matplotlib

matplotlib.use("Agg")  # sin ventana: solo guarda archivos

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.analysis import models as m
from src.analysis.dataset import load_model_dataset
from src.etl.db import ROOT, connect

IMG_DIR = ROOT / "docs" / "img"
LAUNCHES_COLOR, HITS_COLOR = "#2a78d6", "#eb6834"  # paleta categórica validada (slots 1 y 2)

SQL_FIXED_PIE = """
    SELECT extract(year FROM release_date)::int               AS anio,
           count(*)                                           AS lanzamientos,
           count(*) FILTER (WHERE total_reviews >= 100)       AS con_100
    FROM core.v_game_latest
    WHERE is_indie
      AND release_date >= '2014-01-01'
      AND release_date <  date_trunc('year', current_date) - interval '1 year'
    GROUP BY 1
    ORDER BY 1
"""


def fixed_pie_data() -> pd.DataFrame:
    """Lanzamientos indie por año y cuántos llegan a 100 reseñas.
    Se excluye el último año completo: sus juegos aún están acumulando reseñas."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(SQL_FIXED_PIE)
        return pd.DataFrame(cur.fetchall(), columns=["anio", "lanzamientos", "con_100"])


def plot_fixed_pie(data: pd.DataFrame):
    """Barras = lanzamientos; línea = juegos que llegan a 100 reseñas.
    Mismo eje y (ambas son cantidades de juegos)."""
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=110)
    fig.patch.set_facecolor(m.SURFACE)
    ax.set_facecolor(m.SURFACE)

    x = data["anio"].to_numpy()
    ax.bar(x, data["lanzamientos"], width=0.7, color=LAUNCHES_COLOR, alpha=0.85,
           edgecolor=m.SURFACE, linewidth=2, zorder=2)
    ax.plot(x, data["con_100"], color=HITS_COLOR, linewidth=2.5, marker="o",
            markersize=7, markeredgecolor=m.SURFACE, markeredgewidth=1.5, zorder=3)

    # Etiquetas directas en los extremos (no en cada punto)
    first, last = data.iloc[0], data.iloc[-1]
    ax.annotate(f"{int(last['lanzamientos']):,} lanzados".replace(",", "."),
                (last["anio"], last["lanzamientos"]), xytext=(0, 6),
                textcoords="offset points", ha="center", fontsize=9, color=m.TEXT)
    for row in (first, last):
        ax.annotate(f"{int(row['con_100']):,}".replace(",", "."),
                    (row["anio"], row["con_100"]), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=9,
                    color=m.TEXT, fontweight="bold")

    ax.set_xticks(x, [str(a) for a in x])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}".replace(",", "."))
    ax.tick_params(colors=m.TEXT_2, labelsize=9, length=0)
    ax.grid(axis="y", color=m.GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_ylabel("Juegos indie", color=m.TEXT_2, fontsize=10)

    handles = [Patch(facecolor=LAUNCHES_COLOR, alpha=0.85, label="Lanzados en el año"),
               Line2D([0], [0], color=HITS_COLOR, linewidth=2.5, marker="o",
                      markeredgecolor=m.SURFACE, label="Llegan a 100 reseñas o más")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2,
              frameon=False, fontsize=9, labelcolor=m.TEXT_2, borderaxespad=0.3)
    fig.suptitle("Más juegos, los mismos lugares de éxito", x=0.01, ha="left",
                 fontsize=13, color=m.TEXT, fontweight="bold")
    fig.tight_layout()
    return fig


def reach_quality_figure():
    df = load_model_dataset()
    t1 = m.tidy(m.fit(df, "log_resenas", with_tags=False), log_outcome=True)
    t2 = m.tidy(m.fit(df[df["tiene_tags"] == 1], "log_resenas", with_tags=True), log_outcome=True)
    t3 = m.tidy(m.fit(df[df["total_reviews"] >= 50], "pct_positive", with_tags=True), log_outcome=False)
    return m.plot_reach_quality(m.reach_quality_table(t1, t2, t3), "Alcance vs. calidad percibida")


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    figures = {
        "pastel_fijo.png": plot_fixed_pie(fixed_pie_data()),
        "alcance_vs_calidad.png": reach_quality_figure(),
    }
    for name, fig in figures.items():
        fig.savefig(IMG_DIR / name, facecolor=m.SURFACE, bbox_inches="tight")
        plt.close(fig)
        print("Guardada", IMG_DIR / name)


if __name__ == "__main__":
    main()
