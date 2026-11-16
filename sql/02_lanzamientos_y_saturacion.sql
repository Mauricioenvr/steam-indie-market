-- =====================================================================
-- EDA 02 — Pregunta 1: evolución de lanzamientos y saturación
-- Indie = género 'Indie' O tag 'Indie' (ver docs/decisiones_metodologicas.md).
-- Se excluye el año en curso porque está incompleto.
-- =====================================================================

-- 2.1 Lanzamientos por año: total, indie, participación y crecimiento
WITH por_anio AS (
    SELECT extract(year FROM release_date)::int        AS anio,
           count(*)                                    AS total,
           count(*) FILTER (WHERE is_indie)      AS indie
    FROM core.v_game_latest
    WHERE release_date < date_trunc('year', current_date)
    GROUP BY 1
)
SELECT anio, total, indie,
       round(100.0 * indie / total, 1)                                   AS pct_indie,
       -- NULLIF evita dividir entre 0 en años sin indies previos
       round(100.0 * (indie - lag(indie) OVER w) / NULLIF(lag(indie) OVER w, 0), 1) AS crec_indie_pct,
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
WHERE is_indie
  AND release_date >= '2010-01-01'
  AND release_date < date_trunc('year', current_date)
GROUP BY 1
ORDER BY 1;

-- 2.2b Cantidad absoluta de indies que alcanzan cada umbral, por año.
-- Si se mantiene estable mientras los lanzamientos crecen, la atención del
-- mercado es un "pastel fijo": más juegos compiten por los mismos lugares.
SELECT extract(year FROM release_date)::int               AS anio,
       count(*)                                           AS indies,
       count(*) FILTER (WHERE total_reviews >= 100)       AS con_100_o_mas,
       count(*) FILTER (WHERE total_reviews >= 1000)      AS con_1000_o_mas,
       count(*) FILTER (WHERE total_reviews >= 10000)     AS con_10000_o_mas
FROM core.v_game_latest
WHERE is_indie
  AND release_date >= '2010-01-01'
  AND release_date < date_trunc('year', current_date)
GROUP BY 1
ORDER BY 1;

-- 2.3 Estacionalidad: lanzamientos indie por mes y por día de la semana
-- (últimos 5 años completos). El promedio diario corrige que los meses
-- tienen distinto número de días.
WITH lanz AS (
    SELECT d.month, d.month_name, count(*) AS lanzamientos
    FROM core.v_game_latest g
    JOIN core.dim_date d ON d.date_key = g.release_date_key
    WHERE g.is_indie
      AND g.release_date >= date_trunc('year', current_date) - interval '5 years'
      AND g.release_date <  date_trunc('year', current_date)
    GROUP BY 1, 2
), dias AS (
    SELECT month, count(*) AS dias_calendario
    FROM core.dim_date
    WHERE full_date >= date_trunc('year', current_date) - interval '5 years'
      AND full_date <  date_trunc('year', current_date)
    GROUP BY 1
)
SELECT l.month, l.month_name, l.lanzamientos,
       round(100.0 * l.lanzamientos / sum(l.lanzamientos) OVER (), 1) AS pct,
       round(l.lanzamientos::numeric / d.dias_calendario, 1)           AS promedio_diario
FROM lanz l JOIN dias d USING (month)
ORDER BY l.month;

-- Por día de la semana. Se excluyen las fechas que solo traen mes y año
-- ('Oct 2008'), porque se convierten al día 1 y sesgarían el día de la semana.
SELECT d.day_of_week, d.day_name,
       count(*)                                                       AS lanzamientos,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)             AS pct
FROM core.v_game_latest g
JOIN core.dim_date d ON d.date_key = g.release_date_key
WHERE g.is_indie
  AND g.release_date_raw !~ '^[A-Za-z]{3,9} \d{4}$'
  AND g.release_date >= date_trunc('year', current_date) - interval '5 years'
  AND g.release_date <  date_trunc('year', current_date)
GROUP BY 1, 2
ORDER BY 1;

-- 2.4 ¿Influye el momento de lanzamiento en el éxito? (pregunta 4)
-- Cohortes 2016–2023: juegos con al menos ~2 años para acumular reseñas.
-- Ojo: es asociación. Los estudios más grandes o mejor preparados pueden
-- elegir fechas distintas (confusión); la regresión lo controlará después.
SELECT d.month, d.month_name,
       count(*)                                                       AS indies,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY g.total_reviews)   AS mediana_resenas,
       round(100.0 * avg((g.total_reviews >= 100)::int), 1)           AS pct_100_o_mas,
       round(100.0 * avg((g.total_reviews >= 1000)::int), 1)          AS pct_1000_o_mas
FROM core.v_game_latest g
JOIN core.dim_date d ON d.date_key = g.release_date_key
WHERE g.is_indie
  AND g.release_date BETWEEN '2016-01-01' AND '2023-12-31'
GROUP BY 1, 2
ORDER BY 1;

SELECT d.day_of_week, d.day_name,
       count(*)                                                       AS indies,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY g.total_reviews)   AS mediana_resenas,
       round(100.0 * avg((g.total_reviews >= 100)::int), 1)           AS pct_100_o_mas,
       round(100.0 * avg((g.total_reviews >= 1000)::int), 1)          AS pct_1000_o_mas
FROM core.v_game_latest g
JOIN core.dim_date d ON d.date_key = g.release_date_key
WHERE g.is_indie
  AND g.release_date_raw !~ '^[A-Za-z]{3,9} \d{4}$'
  AND g.release_date BETWEEN '2016-01-01' AND '2023-12-31'
GROUP BY 1, 2
ORDER BY 1;
