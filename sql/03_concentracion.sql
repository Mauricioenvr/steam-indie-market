-- =====================================================================
-- EDA 03 — Pregunta 5: ¿qué tan concentrado está el éxito?
-- Universo: juegos indie (género) lanzados antes del año en curso.
-- =====================================================================

-- 3.1 Participación en el total de reseñas por grupo de juegos
WITH indies AS (
    SELECT total_reviews,
           percent_rank() OVER (ORDER BY total_reviews DESC) AS pr   -- 0 = el más reseñado
    FROM core.v_game_latest
    WHERE is_indie_genre AND release_date < date_trunc('year', current_date)
)
SELECT round(100.0 * sum(total_reviews) FILTER (WHERE pr <  0.01) / sum(total_reviews), 1) AS top_1pct,
       round(100.0 * sum(total_reviews) FILTER (WHERE pr <  0.10) / sum(total_reviews), 1) AS top_10pct,
       round(100.0 * sum(total_reviews) FILTER (WHERE pr >= 0.50) / sum(total_reviews), 1) AS mitad_inferior,
       count(*)                                                                             AS indies
FROM indies;

-- 3.2 Coeficiente de Gini de las reseñas, por año de lanzamiento
-- 0 = todos los juegos tienen las mismas reseñas; 1 = un solo juego tiene todas.
-- Si sube con los años, el éxito se concentra cada vez más.
WITH ordenado AS (
    SELECT extract(year FROM release_date)::int AS anio,
           total_reviews::numeric               AS x,
           row_number() OVER (PARTITION BY extract(year FROM release_date)
                              ORDER BY total_reviews) AS i,
           count(*)     OVER (PARTITION BY extract(year FROM release_date)) AS n
    FROM core.v_game_latest
    WHERE is_indie_genre
      AND release_date >= '2010-01-01'
      AND release_date < date_trunc('year', current_date)
)
SELECT anio, max(n) AS indies,
       round(2 * sum(i * x) / (max(n) * nullif(sum(x), 0)) - (max(n) + 1.0) / max(n), 3) AS gini
FROM ordenado
GROUP BY anio
ORDER BY anio;

-- 3.3 Los 20 indies más reseñados (para validar con sentido común)
SELECT name, extract(year FROM release_date)::int AS anio,
       total_reviews, pct_positive, price_usd
FROM core.v_game_latest
WHERE is_indie_genre
ORDER BY total_reviews DESC
LIMIT 20;
