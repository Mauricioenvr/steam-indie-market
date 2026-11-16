"""Gráficas Plotly del dashboard.

Paleta validada (pruebas de daltonismo y contraste): cada métrica conserva su color
en todas las vistas.
"""
import pandas as pd
import plotly.graph_objects as go

VOLUME = "#2a78d6"    # cantidad de juegos
SUCCESS = "#eb6834"   # % que llega a 100 reseñas
RATING = "#1baf7a"    # valoración (% positivo); contraste < 3:1: siempre con etiqueta de valor
BASELINE = "#898781"  # línea base de comparación
FONT = "Inter, -apple-system, Segoe UI, sans-serif"


def _layout(fig: go.Figure, title: str, y_title: str = "", y_suffix: str = "",
            height: int = 360) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        height=height,
        margin=dict(l=10, r=10, t=70, b=10),
        font=dict(family=FONT, size=12),
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom", title=None),
        hovermode="x unified",
        bargap=0.3,
        separators=",.",  # formato en español: 12.345 y 82,5
    )
    fig.update_xaxes(showgrid=False, ticks="")
    fig.update_yaxes(title=y_title, ticksuffix=y_suffix, gridcolor="rgba(128,128,128,0.18)",
                     zeroline=False, rangemode="tozero", tickformat=",~r" if not y_suffix else None)
    return fig


def fixed_pie(by_year: pd.DataFrame) -> go.Figure:
    """Lanzados por año (barras) y cuántos llegan a 100 reseñas (línea), mismo eje."""
    fig = go.Figure()
    fig.add_bar(x=by_year["anio"], y=by_year["juegos"], name="Lanzados en el año",
                marker=dict(color=VOLUME, cornerradius=4),
                hovertemplate="%{y:,} lanzados<extra></extra>")
    fig.add_scatter(x=by_year["anio"], y=by_year["llegan_100"], name="Llegan a 100 reseñas o más",
                    mode="lines+markers", line=dict(color=SUCCESS, width=2.5),
                    marker=dict(size=8, line=dict(width=2, color="white")),
                    hovertemplate="%{y:,} llegan a 100<extra></extra>")
    _layout(fig, "Más juegos, los mismos lugares de éxito", "Juegos indie")
    fig.update_xaxes(dtick=1)
    return fig


def concentration(conc: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=conc["pct_resenas"], y=conc["grupo"], orientation="h",
        marker=dict(color=VOLUME, cornerradius=4),
        texttemplate="%{x:.1f} %", textposition="outside",
        cliponaxis=False, hovertemplate="%{y}: %{x:.1f} % de las reseñas<extra></extra>"))
    _layout(fig, "¿Quién se lleva las reseñas?", height=300)
    fig.update_layout(hovermode="closest", margin=dict(r=60))
    fig.update_xaxes(title="% de todas las reseñas", ticksuffix=" %", showgrid=True,
                     gridcolor="rgba(128,128,128,0.18)", range=[0, 100])
    fig.update_yaxes(autorange="reversed", title="")
    return fig


def bars(df: pd.DataFrame, y: str, title: str, color: str, y_title: str = "",
         y_suffix: str = "", fmt: str = ",.1f", height: int = 330,
         labels: bool = False) -> go.Figure:
    """Barras simples de una métrica por categoría (tramo, día, mes, año).
    labels=True escribe el valor sobre cada barra (obligatorio para RATING)."""
    fig = go.Figure(go.Bar(
        x=df["etiqueta"], y=df[y], marker=dict(color=color, cornerradius=4),
        texttemplate=f"%{{y:{fmt}}}" if labels else None,
        textposition="outside", cliponaxis=False,
        customdata=df[["juegos"]],
        hovertemplate=f"%{{x}}<br>%{{y:{fmt}}}{y_suffix}<br>%{{customdata[0]:,}} juegos<extra></extra>"))
    _layout(fig, title, y_title, y_suffix, height)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(type="category", tickangle=0)
    return fig


def niche_vs_base(niche: pd.DataFrame, base: pd.DataFrame, base_name: str) -> go.Figure:
    """% que llega a 100 reseñas por año: nicho vs. línea base (misma escala)."""
    fig = go.Figure()
    fig.add_scatter(x=base["anio"], y=base["pct_100"], name=base_name, mode="lines+markers",
                    line=dict(color=BASELINE, width=2, dash="dash"), marker=dict(size=6),
                    hovertemplate="%{y:.1f} %<extra>" + base_name + "</extra>")
    fig.add_scatter(x=niche["anio"], y=niche["pct_100"], name="Nicho seleccionado",
                    mode="lines+markers", line=dict(color=SUCCESS, width=2.5),
                    marker=dict(size=8, line=dict(width=2, color="white")),
                    hovertemplate="%{y:.1f} %<extra>Nicho</extra>")
    _layout(fig, "% que llega a 100 reseñas, por año de lanzamiento", y_suffix=" %")
    fig.update_xaxes(dtick=1)
    return fig
