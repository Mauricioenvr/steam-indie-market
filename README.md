# ¿Qué hace que un indie destaque en Steam?

Análisis del mercado de videojuegos indie en Steam: tendencias de lanzamiento,
saturación, géneros, etiquetas, precios y los factores que se asocian con el
**alcance comercial** y con la **calidad percibida** de un juego.

> 🚧 Proyecto en desarrollo.

## Preguntas de investigación

1. ¿Cómo han evolucionado el volumen de lanzamientos indie y la saturación del mercado?
2. ¿Qué etiquetas y géneros se asocian con más reseñas y cuáles con mejor valoración?
3. ¿Qué relación hay entre el precio y el éxito? ¿Existe un rango de precio óptimo?
4. ¿Influyen el mes y el día de lanzamiento, tener demo o salir de Early Access?
5. ¿Qué tan concentrado está el éxito entre los juegos más populares?

## Enfoque

El éxito se mide en **dos dimensiones separadas**: volumen de reseñas (alcance) y
porcentaje de reseñas positivas ajustado por confianza (calidad). Cruzarlas da
cuatro perfiles: *éxito pleno*, *éxito comercial polémico*, *joya oculta* y *fracaso*.
Los resultados son asociaciones, no relaciones causales.
Detalles en [`docs/decisiones_metodologicas.md`](docs/decisiones_metodologicas.md).

## Stack

| Capa | Herramienta |
|---|---|
| Extracción | Python (ijson, requests), Steam Store API, SteamSpy |
| Almacenamiento y modelado | PostgreSQL: staging en JSONB y modelo estrella |
| Análisis | SQL (CTEs, funciones de ventana), pandas, statsmodels, scipy |
| Visualización | matplotlib (notebooks), Streamlit + Plotly (dashboard) |

## Modelo de datos

```
staging.games_raw (JSONB por juego y snapshot)
        │
        ▼
core.dim_game ── bridge_game_tag ── dim_tag
     │       ├── bridge_game_genre ── dim_genre
     │       ├── bridge_game_category ── dim_category
     │       ├── bridge_game_developer ── dim_developer
     │       └── bridge_game_publisher ── dim_publisher
     │
     ├── dim_date (fecha de lanzamiento)
     └── fact_game_snapshot (precio, reseñas, propietarios, CCU, tiempo de juego)
```

Cada carga se guarda como un *snapshot* fechado, de modo que los datos de Kaggle y
las actualizaciones de la API conviven y permiten ver la evolución en el tiempo.

## Estructura

```
├── app/            # Dashboard en Streamlit
├── data/           # raw/ y processed/ (no se versionan)
├── docs/           # Decisiones metodológicas
├── notebooks/      # Exploración y modelos
├── sql/            # Esquema, transformaciones, EDA (eda/) y dataset de modelos (analysis/)
├── src/etl/        # Carga y orquestación del pipeline
├── src/analysis/   # Dataset de modelado, regresiones y gráficos
└── tests/fixtures/ # Datos de muestra para probar el pipeline
```

## Cómo reproducirlo

```bash
# 1. Entorno
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Base de datos
createdb steam_indie
cp .env.example .env               # y completa tus credenciales

# 3. Datos: descarga games.json del dataset de FronkonGames en data/raw/

# 4. Pipeline (usa como snapshot la fecha de actualización del dataset)
python -m src.etl.pipeline --json data/raw/games.json --snapshot-date AAAA-MM-DD
```

### Análisis

- **Exploración en SQL:** `sql/eda/01` a `05`, una consulta a la vez (en pgAdmin, selecciónala y pulsa F5).
- **Regresión:** abre `notebooks/01_regresion.ipynb` en VS Code con el kernel del `.venv`.
  Las figuras se hacen con matplotlib (imágenes estáticas que GitHub muestra);
  el dashboard usa Plotly para las gráficas interactivas.

### Pruebas sin el dataset real

Usa una base de datos aparte para no mezclar datos de prueba con los reales:

```bash
createdb steam_indie_test
# Casos especiales de formato
PGDATABASE=steam_indie_test python -m src.etl.pipeline --json tests/fixtures/sample_games.json --snapshot-date 2026-01-15
# 6.000 juegos sintéticos con efectos conocidos, para validar los modelos
python tests/generate_synthetic_games.py data/raw/synthetic.json --n 6000
PGDATABASE=steam_indie_test python -m src.etl.pipeline --json data/raw/synthetic.json --snapshot-date 2026-11-13
```

## Datos

- [Steam Games Dataset](https://www.kaggle.com/datasets/fronkongames/steam-games-dataset),
  de Fronkon Games, construido con la API de Steam y SteamSpy.
- Steam Store API y SteamSpy para el enriquecimiento.

## Hoja de ruta

- [x] Estructura del repo y modelo de datos
- [x] Carga del dataset base y transformación a modelo estrella
- [ ] Enriquecimiento con Steam API y SteamSpy
- [x] Análisis exploratorio en SQL
- [x] Modelos de regresión (alcance y calidad)
- [ ] Interpretación de los modelos con el snapshot real
- [ ] Dashboard en Streamlit
- [ ] Hallazgos y conclusiones
