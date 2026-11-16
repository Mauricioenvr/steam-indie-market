-- =====================================================================
-- EDA 01 — Calidad de datos y definición de "indie"
-- Ejecuta cada consulta por separado (en pgAdmin: selecciónala y F5).
-- =====================================================================

-- 1.1 Panorama general
SELECT count(*)                                           AS juegos,
       min(release_date)                                  AS primer_lanzamiento,
       max(release_date)                                  AS ultimo_lanzamiento,
       round(100.0 * avg(is_free::int), 1)                AS pct_gratis,
       round(100.0 * avg((total_reviews = 0)::int), 1)    AS pct_sin_resenas,
       round(100.0 * avg((total_reviews < 10)::int), 1)   AS pct_menos_10_resenas,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY total_reviews) AS mediana_resenas,
       round(avg(total_reviews))                          AS media_resenas
FROM core.v_game_latest;
-- Si la media es mucho mayor que la mediana, la distribución está concentrada en pocos juegos.

-- 1.2 ¿Cuánto coinciden el "Indie" como género y como tag?
SELECT is_indie_genre, is_indie_tag,
       count(*)                                           AS juegos,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY total_reviews) AS mediana_resenas
FROM core.v_game_latest
GROUP BY 1, 2
ORDER BY 1 DESC, 2 DESC;
-- Ojo: los tags los vota la comunidad, así que un juego con pocas
-- reseñas puede no tener tags aunque sea indie.

-- 1.3 ¿Los juegos sin tag 'Indie' simplemente no tienen tags?
SELECT is_indie_genre,
       count(*) FILTER (WHERE NOT EXISTS (
           SELECT 1 FROM core.bridge_game_tag b WHERE b.app_id = g.app_id)) AS sin_ningun_tag,
       count(*)                                                             AS total
FROM core.v_game_latest g
GROUP BY 1;

-- 1.4 Juegos por año de lanzamiento: detecta años incompletos o atípicos
SELECT extract(year FROM release_date)::int AS anio, count(*) AS juegos
FROM core.v_game_latest
GROUP BY 1
ORDER BY 1;
