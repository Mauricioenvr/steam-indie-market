-- =====================================================================
-- EDA 02 — Pregunta 1: evolución de lanzamientos y saturación
-- Criterio provisional de indie: género 'Indie' (declarado por el
-- desarrollador). Se revisará con los resultados de EDA 01.
-- Se excluye el año en curso porque está incompleto.
-- =====================================================================

-- 2.1 Lanzamientos por año: total, indie, participación y crecimiento
WITH por_anio AS (
    SELECT extract(year FROM release_date)::int        AS anio,
           count(*)                                    AS total,
           count(*) FILTER (WHERE is_indie_genre)      AS indie
    FROM core.v_game_latest
    WHERE release_date < date_trunc('year', current_date)
    GROUP BY 1
)
SELECT anio, total, indie,
       round(100.0 * indie / total, 1)                                   AS pct_indie,
       round(100.0 * (indie - lag(indie) OVER w) / lag(indie) OVER w, 1) AS crec_indie_pct,
       sum(indie) OVER (ORDER BY anio)                                   AS indie_acumulado
FROM por_anio
WINDOW w AS (ORDER BY anio)
ORDER BY anio;

-- 2.2 ¿Hay más competencia por la atención? Reseñas por juego indie según año
-- ADVERTENCIA: las reseñas son acumuladas. Un juego de 2015 lleva 10 años
-- sumando reseñas y uno de 2024 solo uno, así que la mediana de los años
-- recientes siempre sale más baja. Por eso la métrica más justa es la
-- proporción de juegos que superan umbrales, comparando cohortes de edad
-- parecida (o con la API, reseñas en los primeros N meses).
SELECT extract(year FROM release_date)::int                         AS anio,
       count(*)                                                     AS indies,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY total_reviews)  AS mediana_resenas,
       percentile_cont(0.9)  WITHIN GROUP (ORDER BY total_reviews)  AS p90_resenas,
       round(100.0 * avg((total_reviews >= 100)::int), 1)           AS pct_100_o_mas,
       round(100.0 * avg((total_reviews >= 1000)::int), 1)          AS pct_1000_o_mas,
       round(100.0 * avg((total_reviews < 10)::int), 1)             AS pct_menos_10
FROM core.v_game_latest
WHERE is_indie_genre
  AND release_date >= '2010-01-01'
  AND release_date < date_trunc('year', current_date)
GROUP BY 1
ORDER BY 1;

-- 2.3 Estacionalidad: lanzamientos indie por mes y por día de la semana
-- (últimos 5 años completos)
SELECT d.month, d.month_name,
       count(*)                                                       AS lanzamientos,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)             AS pct
FROM core.v_game_latest g
JOIN core.dim_date d ON d.date_key = g.release_date_key
WHERE g.is_indie_genre
  AND g.release_date >= date_trunc('year', current_date) - interval '5 years'
  AND g.release_date <  date_trunc('year', current_date)
GROUP BY 1, 2
ORDER BY 1;

SELECT d.day_of_week, d.day_name,
       count(*)                                                       AS lanzamientos,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)             AS pct
FROM core.v_game_latest g
JOIN core.dim_date d ON d.date_key = g.release_date_key
WHERE g.is_indie_genre
  AND g.release_date >= date_trunc('year', current_date) - interval '5 years'
  AND g.release_date <  date_trunc('year', current_date)
GROUP BY 1, 2
ORDER BY 1;
