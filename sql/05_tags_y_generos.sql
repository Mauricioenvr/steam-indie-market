-- =====================================================================
-- EDA 05 — Pregunta 2: ¿qué géneros y tags se asocian con el éxito?
-- Universo: indies publicados 2016–2023, sin software.
--
-- GÉNEROS: los declara el desarrollador y existen para todos los juegos.
-- TAGS: los vota la comunidad, así que solo existen para juegos con jugadores.
--   Los juegos con tags son, por construcción, más exitosos que el promedio.
--   Por eso cada tag se compara contra la línea base de los JUEGOS CON TAGS,
--   nunca contra el total. Se usan los 5 tags más votados de cada juego
--   (los que lo definen) y solo tags presentes en 200 o más juegos.
-- =====================================================================

-- 5.1 Éxito por género (un juego puede tener varios géneros)
WITH base AS (
    SELECT app_id, total_reviews, pct_positive
    FROM core.v_game_latest
    WHERE is_indie AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
)
SELECT ge.name                                                        AS genero,
       count(*)                                                       AS indies,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY b.total_reviews)   AS mediana_resenas,
       round(100.0 * avg((b.total_reviews >= 100)::int), 1)           AS pct_100_o_mas,
       round(100.0 * avg((b.total_reviews >= 1000)::int), 1)         AS pct_1000_o_mas,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY b.pct_positive)
           FILTER (WHERE b.total_reviews >= 50)                       AS mediana_pct_positivo
FROM base b
JOIN core.bridge_game_genre bg USING (app_id)
JOIN core.dim_genre ge USING (genre_id)
WHERE ge.name <> 'Indie'
GROUP BY 1
HAVING count(*) >= 100
ORDER BY pct_100_o_mas DESC;

-- 5.2 Tags con mejor y peor alcance (20 de cada extremo)
-- indice_vs_base > 1 = el tag supera a la línea base de juegos con tags.
WITH base AS (
    SELECT app_id, total_reviews, pct_positive
    FROM core.v_game_latest
    WHERE is_indie AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
), con_tag AS (
    SELECT b.*, t.name AS tag
    FROM base b
    JOIN core.bridge_game_tag bt USING (app_id)
    JOIN core.dim_tag t USING (tag_id)
    WHERE bt.tag_rank <= 5 AND t.name <> 'Indie'
), linea_base AS (
    SELECT avg((total_reviews >= 100)::int) AS base_100
    FROM base
    WHERE app_id IN (SELECT app_id FROM con_tag)
), stats AS (
    SELECT tag,
           count(*)                                                     AS indies,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY total_reviews)   AS mediana_resenas,
           avg((total_reviews >= 100)::int)                             AS p100,
           round(100.0 * avg((total_reviews >= 1000)::int), 1)          AS pct_1000_o_mas,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_positive)
               FILTER (WHERE total_reviews >= 50)                       AS mediana_pct_positivo
    FROM con_tag
    GROUP BY tag
    HAVING count(*) >= 200
), ranking AS (
    SELECT s.*, rank() OVER (ORDER BY p100 DESC) AS puesto, count(*) OVER () AS total_tags
    FROM stats s
)
SELECT r.puesto, r.tag, r.indies, r.mediana_resenas,
       round(100.0 * r.p100, 1)                 AS pct_100_o_mas,
       r.pct_1000_o_mas, r.mediana_pct_positivo,
       round(r.p100 / lb.base_100, 2)           AS indice_vs_base
FROM ranking r CROSS JOIN linea_base lb
WHERE r.puesto <= 20 OR r.puesto > r.total_tags - 20
ORDER BY r.puesto;

-- 5.3 Nichos: alcance vs. crecimiento de la oferta
-- crecimiento_oferta = participación del tag en 2020–2023 / participación en
-- 2016–2019. Menor que 1: el nicho pierde peso relativo (menos competencia nueva).
-- Se listan solo tags que superan la línea base de alcance, ordenados del
-- nicho que menos creció al que más.
WITH base AS (
    SELECT app_id, total_reviews, release_date
    FROM core.v_game_latest
    WHERE is_indie AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
), con_tag AS (
    SELECT b.*, t.name AS tag, (b.release_date >= '2020-01-01') AS reciente
    FROM base b
    JOIN core.bridge_game_tag bt USING (app_id)
    JOIN core.dim_tag t USING (tag_id)
    WHERE bt.tag_rank <= 5 AND t.name <> 'Indie'
), totales AS (
    SELECT count(DISTINCT app_id) FILTER (WHERE NOT reciente) AS n_antes,
           count(DISTINCT app_id) FILTER (WHERE reciente)     AS n_despues,
           (SELECT avg((total_reviews >= 100)::int) FROM base
             WHERE app_id IN (SELECT app_id FROM con_tag))    AS base_100
    FROM con_tag
), stats AS (
    SELECT tag,
           count(*)                                   AS indies,
           count(*) FILTER (WHERE NOT reciente)       AS antes,
           count(*) FILTER (WHERE reciente)           AS despues,
           avg((total_reviews >= 100)::int)           AS p100
    FROM con_tag
    GROUP BY tag
    HAVING count(*) >= 200
)
SELECT s.tag, s.indies,
       round(100.0 * s.p100, 1)                                              AS pct_100_o_mas,
       round(s.p100 / t.base_100, 2)                                         AS indice_vs_base,
       round((s.despues::numeric / t.n_despues)
             / NULLIF(s.antes::numeric / t.n_antes, 0), 2)                   AS crecimiento_oferta
FROM stats s CROSS JOIN totales t
WHERE s.p100 > t.base_100
ORDER BY crecimiento_oferta
LIMIT 25;

-- 5.4 Early Access vs. lanzamiento directo
-- Nota: el género 'Early Access' refleja el estado al momento del snapshot.
SELECT is_early_access,
       count(*)                                                       AS indies,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY total_reviews)     AS mediana_resenas,
       round(100.0 * avg((total_reviews >= 100)::int), 1)             AS pct_100_o_mas,
       round(100.0 * avg((total_reviews >= 1000)::int), 1)            AS pct_1000_o_mas,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_positive)
           FILTER (WHERE total_reviews >= 50)                         AS mediana_pct_positivo
FROM core.v_game_latest
WHERE is_indie AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
GROUP BY 1;
