"""Dashboard: ¿Qué hace que un indie destaque en Steam?

Ejecutar desde la raíz del repo:
    streamlit run app/app.py
"""
import pandas as pd
import streamlit as st

import charts
import data

st.set_page_config(page_title="Indies en Steam", page_icon="🎮", layout="wide")

games, tags, genres, meta = data.load()
Y = data.years(meta)

st.title("¿Qué hace que un indie destaque en Steam?")
st.caption(
    f"Snapshot del {meta['snapshot_date']} · {meta['fuente']} · "
    f"{meta['juegos']:,} indies publicados desde 2014 (sin software). "
    "Alcance = reseñas (proxy de ventas); calidad = % de reseñas positivas en juegos "
    f"con {data.MIN_REVIEWS_RATING} o más reseñas. "
    "[Repositorio y metodología](https://github.com/Mauricioenvr/steam-indie-market)"
)

tab_panorama, tab_nichos, tab_precio = st.tabs(
    ["Panorama del mercado", "Explorador de nichos", "Precio y momento"])


def fmt_n(v) -> str:
    return "—" if pd.isna(v) else f"{v:,.0f}".replace(",", ".")


def fmt_pct(v) -> str:
    return "—" if pd.isna(v) else f"{v:.1f} %".replace(".", ",")


def fmt_delta(v, unit: str, suffix: str) -> str | None:
    """'+4,7 pp vs. base': solo el número lleva coma decimal."""
    return None if pd.isna(v) else f"{v:+.1f}".replace(".", ",") + f" {unit} {suffix}"


# =====================================================================
# 1. Panorama del mercado
# =====================================================================
with tab_panorama:
    maduro = Y["ultimo_maduro"]
    por_anio = (games[games["anio"].between(2014, maduro)]
                .groupby("anio")
                .agg(juegos=("app_id", "size"), llegan_100=("llega_100", "sum"))
                .reset_index())
    p_ini = 100 * por_anio.loc[por_anio["anio"] == 2016, "llegan_100"].sum() / \
        max(por_anio.loc[por_anio["anio"] == 2016, "juegos"].sum(), 1)
    p_fin = 100 * por_anio.iloc[-1]["llegan_100"] / por_anio.iloc[-1]["juegos"]
    ult = games[games["anio"] == Y["ultimo_completo"]]
    prev = games[games["anio"] == Y["ultimo_completo"] - 1]
    conc = data.concentration(games[games["anio"] <= Y["ultimo_completo"]])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Indies publicados desde 2014", fmt_n(len(games)))
    c2.metric(f"Lanzados en {Y['ultimo_completo']}", fmt_n(len(ult)),
              delta=f"{100 * (len(ult) / max(len(prev), 1) - 1):+.0f} % vs. {Y['ultimo_completo'] - 1}")
    c3.metric(f"Llegan a 100 reseñas ({maduro})", fmt_pct(p_fin),
              delta=fmt_delta(p_fin - p_ini, "pp", "vs. 2016"), delta_color="normal")
    c4.metric("Reseñas del 1 % más reseñado", fmt_pct(conc.iloc[0]["pct_resenas"]))

    st.plotly_chart(charts.fixed_pie(por_anio), width="stretch")
    st.caption(
        f"Se muestra hasta {maduro}: los juegos de {Y['ultimo_completo']} todavía están "
        "acumulando reseñas. Mientras los lanzamientos crecen, la cantidad de indies que "
        "llega a 100 reseñas se mantiene casi constante: más juegos compiten por los mismos "
        "lugares de éxito."
    )

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.plotly_chart(charts.concentration(conc), width="stretch")
    with col_b:
        st.markdown("#### Cómo leerlo")
        st.markdown(
            f"- El **1 %** de los indies más reseñados acumula el "
            f"**{fmt_pct(conc.iloc[0]['pct_resenas'])}** de todas las reseñas.\n"
            f"- La **mitad** menos reseñada apenas suma el "
            f"**{fmt_pct(conc.iloc[3]['pct_resenas'])}**.\n"
            f"- {fmt_pct(100 * (games['total_reviews'] == 0).mean())} de los indies no tiene "
            "ninguna reseña."
        )

# =====================================================================
# 2. Explorador de nichos
# =====================================================================
with tab_nichos:
    st.markdown(
        "Elige una combinación de tags, géneros y precio para ver cuántos juegos compiten "
        "en ese nicho y cómo les va frente al resto del mercado."
    )
    tag_counts = tags["tag"].value_counts()
    tag_options = tag_counts[tag_counts >= 50].index.tolist()
    genre_options = genres["genero"].value_counts().index.tolist()
    tramo_options = [t for t in games.sort_values("tramo_precio")["tramo"].dropna().unique()]

    f1, f2, f3 = st.columns([2, 2, 2])
    sel_tags = f1.multiselect("Tags (el juego debe tener todos)", tag_options,
                              help="Se usan los 5 tags más votados de cada juego.")
    sel_genres = f2.multiselect("Géneros (todos)", genre_options)
    sel_tramos = f3.multiselect("Precio de lista", tramo_options,
                                help="Precio sin descuento. Vacío = todos.")
    rango = st.slider("Años de lanzamiento", 2014, Y["ultimo_completo"],
                      (2016, Y["ultimo_cohorte"]),
                      help=f"Por defecto 2016–{Y['ultimo_cohorte']}: los juegos más recientes "
                           "todavía están acumulando reseñas.")

    universe = games[games["anio"].between(*rango)]
    niche = universe
    for t in sel_tags:
        niche = niche[niche["app_id"].isin(tags.loc[tags["tag"] == t, "app_id"])]
    for g in sel_genres:
        niche = niche[niche["app_id"].isin(genres.loc[genres["genero"] == g, "app_id"])]
    if sel_tramos:
        niche = niche[niche["tramo"].isin(sel_tramos)]

    # Los tags solo existen en juegos que tuvieron jugadores: si se filtra por tag,
    # la comparación justa es contra los juegos que también tienen tags.
    if sel_tags:
        base, base_name = universe[universe["tiene_tags"]], "Juegos con tags"
    else:
        base, base_name = universe, "Todo el mercado"

    s_n, s_b = data.summary(niche), data.summary(base)
    if not (sel_tags or sel_genres or sel_tramos):
        st.info("Selecciona al menos un tag, género o tramo de precio para definir un nicho.")
    elif s_n["n"] == 0:
        st.warning("Ningún juego cumple esos filtros. Prueba con menos condiciones.")
    else:
        if s_n["n"] < 30:
            st.warning(f"Solo {s_n['n']} juegos: los porcentajes pueden variar mucho.")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Juegos en el nicho", fmt_n(s_n["n"]),
                  delta=f"{100 * s_n['n'] / max(len(universe), 1):.1f}".replace(".", ",") + " % del mercado",
                  delta_color="off")
        k2.metric("Llegan a 100 reseñas", fmt_pct(s_n["pct_100"]),
                  delta=fmt_delta(s_n["pct_100"] - s_b["pct_100"], "pp", "vs. base"))
        k3.metric("Mediana de reseñas", fmt_n(s_n["mediana_resenas"]),
                  delta=f"base: {fmt_n(s_b['mediana_resenas'])}", delta_color="off")
        k4.metric(f"Valoración mediana ({data.MIN_REVIEWS_RATING}+ reseñas)",
                  fmt_pct(s_n["valoracion"]),
                  delta=fmt_delta(s_n["valoracion"] - s_b["valoracion"], "pp", "vs. base"))
        st.caption(f"Línea base: **{base_name.lower()}** en los mismos años.")

        lanz = data.by_group(niche, "anio")
        maduro_rng = (rango[0], min(rango[1], Y["ultimo_maduro"]))
        exito_n = data.by_group(niche[niche["anio"].between(*maduro_rng)], "anio")
        exito_b = data.by_group(base[base["anio"].between(*maduro_rng)], "anio")

        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(charts.bars(lanz, "juegos", "Lanzamientos del nicho por año",
                                        charts.VOLUME, fmt=",.0f"), width="stretch")
        with g2:
            st.plotly_chart(charts.niche_vs_base(exito_n, exito_b, base_name),
                            width="stretch")

        st.markdown("#### Juegos más reseñados del nicho")
        top = (niche.nlargest(15, "total_reviews")
                    [["name", "anio", "total_reviews", "pct_positive", "list_price_usd"]])
        st.dataframe(
            top, hide_index=True, width="stretch",
            column_config={
                "name": "Juego", "anio": st.column_config.NumberColumn("Año", format="%d"),
                "total_reviews": st.column_config.NumberColumn("Reseñas", format="%d"),
                "pct_positive": st.column_config.NumberColumn("% positivo", format="%.1f %%"),
                "list_price_usd": st.column_config.NumberColumn("Precio de lista", format="$%.2f"),
            })

    with st.expander("¿Por qué la línea base cambia cuando eliges un tag?"):
        st.markdown(
            "Los tags los vota la comunidad, así que solo existen en juegos que tuvieron "
            "jugadores: alrededor de 4 de cada 10 indies no tienen ninguno. Si comparáramos un "
            "tag contra todo el mercado, cualquier tag parecería exitoso. Por eso, al filtrar "
            "por tag, el nicho se compara solo contra los juegos que también tienen tags."
        )

# =====================================================================
# 3. Precio y momento
# =====================================================================
with tab_precio:
    st.markdown(
        "Datos descriptivos: cómo se distribuyen los lanzamientos y cómo les va según el "
        "precio y la fecha. Los efectos controlados (modelos de regresión) están en el "
        "[notebook](https://github.com/Mauricioenvr/steam-indie-market/blob/main/notebooks/01_regresion.ipynb)."
    )
    rango_p = st.slider("Años de lanzamiento", 2014, Y["ultimo_completo"],
                        (2016, Y["ultimo_cohorte"]), key="rango_precio")
    sub = games[games["anio"].between(*rango_p)]

    st.subheader("Precio de lista")
    orden_tramos = sorted(sub["tramo_precio"].dropna().unique(), key=str)
    precio = data.by_group(sub, "tramo_precio", order=orden_tramos)
    precio["etiqueta"] = (precio["tramo_precio"].astype(str).str.split(". ", n=1).str[1]
                          .str.replace(" – ", "–<br>", regex=False)
                          .str.replace(" o más", "<br>o más", regex=False))
    p1, p2, p3 = st.columns(3)
    p1.plotly_chart(charts.bars(precio, "pct_juegos", "¿A qué precio se lanzan?",
                                charts.VOLUME, y_suffix=" %"), width="stretch")
    p2.plotly_chart(charts.bars(precio, "pct_100", "¿Cuántos llegan a 100 reseñas?",
                                charts.SUCCESS, y_suffix=" %"), width="stretch")
    p3.plotly_chart(charts.bars(precio, "valoracion", "Valoración mediana",
                                charts.RATING, y_suffix=" %", labels=True),
                    width="stretch")
    st.caption(
        "En los modelos con controles, el precio se asocia fuertemente con el alcance pero no "
        "con la valoración (salvo por debajo de $2). El precio refleja en buena parte la "
        "ambición del proyecto y es el precio actual, no el de lanzamiento."
    )

    st.subheader("Día de la semana")
    dias = data.by_group(sub.dropna(subset=["dia_semana"]), "dia_semana",
                         order=list(range(1, 8)), labels=data.DAYS)
    d1, d2 = st.columns(2)
    d1.plotly_chart(charts.bars(dias, "pct_juegos", "¿Qué día se lanzan?",
                                charts.VOLUME, y_suffix=" %"), width="stretch")
    d2.plotly_chart(charts.bars(dias, "pct_100", "¿Cuántos llegan a 100 reseñas?",
                                charts.SUCCESS, y_suffix=" %"), width="stretch")
    st.caption(
        "Con controles (precio, publisher, géneros…), el jueves sigue siendo el mejor día y el "
        "fin de semana el peor (sábado −25 %, domingo −21 % de reseñas frente al jueves)."
    )

    st.subheader("Mes")
    dias_mes = (pd.Series(pd.date_range(f"{rango_p[0]}-01-01", f"{rango_p[1]}-12-31"))
                  .dt.month.value_counts())
    meses = data.by_group(sub, "mes", order=list(range(1, 13)), labels=data.MONTHS)
    meses["por_dia"] = meses["juegos"] / meses["mes"].map(dias_mes)
    m1, m2 = st.columns(2)
    m1.plotly_chart(charts.bars(meses, "por_dia", "Lanzamientos por día (promedio)",
                                charts.VOLUME), width="stretch")
    m2.plotly_chart(charts.bars(meses, "pct_100", "¿Cuántos llegan a 100 reseñas?",
                                charts.SUCCESS, y_suffix=" %"), width="stretch")
    st.caption(
        "Octubre y noviembre concentran más lanzamientos por día. Con controles, enero es el "
        "mejor mes y noviembre–diciembre rinden ~30 % menos; una prueba con cohortes antiguas "
        "confirma que es estacionalidad y no antigüedad."
    )
