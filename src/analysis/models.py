"""Modelos de regresión, tabla de coeficientes y gráfico de efectos."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import statsmodels.formula.api as smf

from src.analysis.dataset import DESIGN_TAGS, GENRES, slug

REF_PRICE = "3. $5 – 9,99"
REF_DAY = 4  # jueves

CONTROLS = [
    f"C(tramo_precio, Treatment('{REF_PRICE}'))",
    "C(anio)",                                   # controla la antigüedad de la cohorte
    "C(mes)",
    f"C(dia_semana, Treatment({REF_DAY}))",
    "autopublicado", "is_early_access",
    "log_idiomas", "audio_completo", "mac", "linux",
    "tiene_logros", "log_capturas", "tiene_trailer", "has_website", "tiene_dlc",
]
GENRE_TERMS = [slug(g, "gen_") for g in GENRES]
TAG_TERMS = [slug(t, "tag_") for t in DESIGN_TAGS]


def formula(df: pd.DataFrame, y: str, with_tags: bool) -> str:
    """Arma la fórmula descartando variables sin variación en la muestra
    (p. ej. un tag ausente), que harían la matriz singular."""
    terms = CONTROLS + GENRE_TERMS + (TAG_TERMS if with_tags else [])
    keep = [t for t in terms if t.startswith("C(") or df[t].nunique() > 1]
    return f"{y} ~ " + " + ".join(keep)


def fit(df: pd.DataFrame, y: str, with_tags: bool):
    """OLS con errores estándar robustos a heterocedasticidad (HC3)."""
    return smf.ols(formula(df, y, with_tags), data=df).fit(cov_type="HC3")


# ---------------------------------------------------------------------
# Etiquetas legibles
# ---------------------------------------------------------------------
DAYS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 5: "Viernes", 6: "Sábado", 7: "Domingo"}
MONTHS = {2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio",
          8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
SIMPLE = {
    "autopublicado": "Autopublicado (sin publisher externo)",
    "is_early_access": "Sigue en Early Access",
    "log_idiomas": "Idiomas soportados (×2,7)",
    "audio_completo": "Tiene audio completo en algún idioma",
    "mac": "Disponible en Mac",
    "linux": "Disponible en Linux",
    "tiene_logros": "Tiene logros",
    "log_capturas": "Capturas en la tienda (×2,7)",
    "tiene_trailer": "Tiene tráiler",
    "has_website": "Tiene sitio web",
    "tiene_dlc": "Tiene DLC",
}
SIMPLE |= {slug(g, "gen_"): g for g in GENRES}
SIMPLE |= {slug(t, "tag_"): t for t in DESIGN_TAGS}


def _label(term: str) -> tuple[str, str]:
    """Devuelve (etiqueta, grupo) de un término de statsmodels."""
    if term.startswith("C(tramo_precio"):
        tramo = term.split("[T.")[1].rstrip("]")
        return f"{tramo.split('. ', 1)[1]} (vs $5 – 9,99)", "Precio"
    if term.startswith("C(dia_semana"):
        d = int(float(term.split("[T.")[1].rstrip("]")))
        return f"{DAYS[d]} (vs jueves)", "Día de lanzamiento"
    if term.startswith("C(mes)"):
        m = int(float(term.split("[T.")[1].rstrip("]")))
        return f"{MONTHS[m]} (vs enero)", "Mes de lanzamiento"
    if term.startswith("C(anio)"):
        return term.split("[T.")[1].rstrip("]"), "Año (control)"
    if term.startswith("gen_"):
        return SIMPLE[term], "Género"
    if term.startswith("tag_"):
        return SIMPLE[term], "Tag de diseño"
    return SIMPLE.get(term, term), "Características"


def tidy(result, log_outcome: bool) -> pd.DataFrame:
    """Tabla de coeficientes con IC 95 % y efecto interpretable.

    log_outcome=True: el efecto se expresa como % de cambio en (reseñas + 1).
    log_outcome=False: el efecto queda en las unidades de y (puntos porcentuales).
    """
    ci = result.conf_int()
    out = pd.DataFrame({
        "term": result.params.index,
        "coef": result.params.values,
        "ci_low": ci[0].values,
        "ci_high": ci[1].values,
        "p_value": result.pvalues.values,
    })
    out = out[out["term"] != "Intercept"]
    out[["label", "grupo"]] = out["term"].apply(lambda t: pd.Series(_label(t)))
    if log_outcome:
        for c in ["coef", "ci_low", "ci_high"]:
            out[c.replace("coef", "efecto").replace("ci_", "efecto_")] = 100 * (np.exp(out[c]) - 1)
    else:
        out["efecto"], out["efecto_low"], out["efecto_high"] = out["coef"], out["ci_low"], out["ci_high"]
    out["significativo"] = (out["ci_low"] > 0) | (out["ci_high"] < 0)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------
# Gráfico de efectos (forest plot) con matplotlib: genera PNG directamente,
# que GitHub muestra sin dependencias extra.
# ---------------------------------------------------------------------
# Paleta validada (azul/rojo pasan las pruebas de daltonismo); el signo también
# se lee por la posición respecto a la línea de cero.
COLORS = {"Positivo": "#2a78d6", "Negativo": "#e34948", "No significativo": "#a3a29c"}
SURFACE, TEXT, TEXT_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e8e7e3"


def show(fig) -> None:
    """Muestra la figura en el notebook."""
    plt.show()


def plot_effects(table: pd.DataFrame, title: str, unit: str,
                 groups: list[str] | None = None):
    """unit: '%' (cambio porcentual en reseñas) o 'pp' (puntos porcentuales).

    Cada grupo forma un bloque (el primero arriba); dentro del bloque, de mayor
    a menor efecto.
    """
    t = table if groups is None else table[table["grupo"].isin(groups)]
    order = groups or list(dict.fromkeys(t["grupo"]))
    t = (t.assign(_g=t["grupo"].map({g: i for i, g in enumerate(order)}))
          .sort_values(["_g", "efecto"], ascending=[True, False])
          .reset_index(drop=True))
    estado = np.where(~t["significativo"], "No significativo",
                      np.where(t["efecto"] > 0, "Positivo", "Negativo"))
    suf = "%" if unit == "%" else " pp"

    # Posiciones verticales, con un hueco entre bloques
    y, pos, prev = [], 0.0, None
    for g in t["_g"]:
        if prev is not None and g != prev:
            pos += 0.6
        y.append(pos)
        pos, prev = pos + 1, g
    y = -np.array(y)  # el primer elemento arriba

    fig, ax = plt.subplots(figsize=(9, 0.32 * len(t) + 1.6), dpi=110)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for est, color in COLORS.items():
        sel = estado == est
        if not sel.any():
            continue
        s = t[sel]
        ax.hlines(y[sel], s["efecto_low"], s["efecto_high"], color=color, linewidth=2)
        ax.scatter(s["efecto"], y[sel], s=55, color=color, edgecolors=SURFACE,
                   linewidths=1.5, zorder=3)

    ax.axvline(0, color=TEXT_2, linewidth=1, zorder=1)
    # '$' se escapa: matplotlib interpreta el texto entre dos '$' como fórmula
    ax.set_yticks(y, t["label"].str.replace("$", r"\$", regex=False), color=TEXT, fontsize=10)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors=TEXT_2, labelsize=9)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}{suf}" if v else f"0{suf}")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xlabel("Cambio en reseñas (%)" if unit == "%" else "Cambio en % positivo (pp)",
                  color=TEXT_2, fontsize=10)

    present = [e for e in COLORS if (estado == e).any()]
    handles = [Line2D([0], [0], marker="o", color=COLORS[e], markeredgecolor=SURFACE,
                      markersize=8, linewidth=2, label=e) for e in present]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(handles),
              frameon=False, fontsize=9, labelcolor=TEXT_2, handletextpad=0.4, borderaxespad=0.3)
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, color=TEXT, fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------
# Alcance vs. calidad: mapa de cuadrantes
# ---------------------------------------------------------------------
# Paleta categórica validada (todas las parejas pasan CVD); el aguamarina tiene
# contraste < 3:1, por eso cada grupo usa además una forma de marcador distinta
# y los puntos llevan etiqueta.
GROUP_STYLE = {
    "Tag de diseño": ("#2a78d6", "o"),
    "Género": ("#eb6834", "s"),
    "Publicación": ("#1baf7a", "D"),
}
PUBLICATION_TERMS = {"autopublicado", "is_early_access"}


def reach_quality_table(t_reach: pd.DataFrame, t_reach_tags: pd.DataFrame,
                        t_quality: pd.DataFrame) -> pd.DataFrame:
    """Une el efecto en alcance (modelos 1 y 2) con el efecto en calidad (modelo 3).

    Incluye géneros (modelo 1), tags de diseño (modelo 2) y dos variables de
    publicación (autopublicado y Early Access). Se omiten DLC, logros, Mac, etc.,
    porque reflejan sobre todo causalidad inversa.
    """
    reach = pd.concat([
        t_reach[t_reach["grupo"].eq("Género") | t_reach["term"].isin(PUBLICATION_TERMS)],
        t_reach_tags[t_reach_tags["grupo"].eq("Tag de diseño")],
    ])
    out = reach.merge(t_quality[["term", "efecto", "significativo"]], on="term",
                      suffixes=("_alcance", "_calidad"))
    out["grupo"] = np.where(out["term"].isin(PUBLICATION_TERMS), "Publicación", out["grupo"])
    out["x"] = out["coef"]  # escala log: +100 % y −50 % quedan a la misma distancia del 0
    out["sig_ambos"] = out["significativo_alcance"] & out["significativo_calidad"]
    out["sig_alguno"] = out["significativo_alcance"] | out["significativo_calidad"]
    return out[["term", "label", "grupo", "x", "efecto_alcance", "efecto_calidad",
                "significativo_alcance", "significativo_calidad", "sig_ambos", "sig_alguno"]]


def plot_reach_quality(cross: pd.DataFrame, title: str):
    """Dispersión alcance (x) vs. calidad (y). Se etiquetan los factores
    significativos en ambos modelos; los demás quedan como contexto."""
    from adjustText import adjust_text

    fig, ax = plt.subplots(figsize=(10, 7.5), dpi=110)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    ax.axhline(0, color=TEXT_2, linewidth=1, zorder=1)
    ax.axvline(0, color=TEXT_2, linewidth=1, zorder=1)

    texts = []
    for grupo, (color, marker) in GROUP_STYLE.items():
        g = cross[cross["grupo"] == grupo]
        strong, weak = g[g["sig_ambos"]], g[~g["sig_ambos"]]
        ax.scatter(weak["x"], weak["efecto_calidad"], s=40, marker=marker,
                   facecolors="none", edgecolors=color, linewidths=1.2, alpha=0.55, zorder=2)
        ax.scatter(strong["x"], strong["efecto_calidad"], s=70, marker=marker, color=color,
                   edgecolors=SURFACE, linewidths=1.5, zorder=3)
        for _, r in strong.iterrows():
            texts.append(ax.text(r["x"], r["efecto_calidad"], r["label"], fontsize=9, color=TEXT))

    # Eje x en %, con marcas en valores redondos
    pcts = np.array([-50, -25, 0, 50, 100, 200, 300])
    lo, hi = cross["x"].min(), cross["x"].max()
    ticks = np.log1p(pcts / 100)
    keep = (ticks >= lo - 0.3) & (ticks <= hi + 0.3)
    ax.set_xticks(ticks[keep], [f"{p:+d}%" if p else "0%" for p in pcts[keep]])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.0f} pp" if v else "0 pp")
    ax.tick_params(colors=TEXT_2, labelsize=9, length=0)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_xlabel("Efecto en alcance (cambio en reseñas)", color=TEXT_2, fontsize=10)
    ax.set_ylabel("Efecto en calidad (% positivo, pp)", color=TEXT_2, fontsize=10)

    # Nombres de los cuadrantes
    quad = dict(fontsize=10, color=TEXT_2, fontweight="bold", alpha=0.8)
    ax.text(0.99, 0.98, "Alcance ↑ · calidad ↑", transform=ax.transAxes, ha="right", va="top", **quad)
    ax.text(0.01, 0.98, "Joya oculta", transform=ax.transAxes, ha="left", va="top", **quad)
    ax.text(0.99, 0.02, "Éxito comercial polémico", transform=ax.transAxes, ha="right", va="bottom", **quad)
    ax.text(0.01, 0.02, "Alcance ↓ · calidad ↓", transform=ax.transAxes, ha="left", va="bottom", **quad)

    adjust_text(texts, ax=ax, expand=(1.15, 1.4),
                arrowprops=dict(arrowstyle="-", color=TEXT_2, lw=0.5))

    handles = [Line2D([0], [0], marker=mk, color=c, linestyle="", markersize=8,
                      markeredgecolor=SURFACE, label=g) for g, (c, mk) in GROUP_STYLE.items()]
    handles.append(Line2D([0], [0], marker="o", color=TEXT_2, linestyle="", markersize=7,
                          markerfacecolor="none", alpha=0.6, label="Significativo solo en uno o ninguno"))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4,
              frameon=False, fontsize=9, labelcolor=TEXT_2, handletextpad=0.3, borderaxespad=0.3)
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, color=TEXT, fontweight="bold")
    fig.tight_layout()
    return fig
