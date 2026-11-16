-- =====================================================================
-- EDA 04 — Pregunta 3: relación entre precio y éxito
-- Universo: indies publicados 2016–2023 (al menos ~2 años para acumular
-- reseñas), sin software. Se usa el precio de LISTA (sin descuento).
-- Limitación: es el precio actual; pudo haber bajado desde el lanzamiento.
-- =====================================================================

-- El tramo de precio (columna tramo_precio) se calcula en core.v_game_all.
-- Todas las consultas usan el mismo universo:
--   is_indie AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
--   AND tramo_precio IS NOT NULL

-- 4.1 ¿A qué precio se lanzan los indies? (oferta)
SELECT tramo_precio,
       count(*)                                           AS indies,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM core.v_game_latest
WHERE is_indie
  AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
  AND tramo_precio IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- 4.2 Éxito por tramo de precio: alcance y calidad
-- La valoración se calcula solo con juegos de 50 o más reseñas: con menos,
-- el porcentaje es demasiado inestable.
SELECT tramo_precio,
       count(*)                                                        AS indies,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY total_reviews)      AS mediana_resenas,
       round(100.0 * avg((total_reviews >= 100)::int), 1)              AS pct_100_o_mas,
       round(100.0 * avg((total_reviews >= 1000)::int), 1)             AS pct_1000_o_mas,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_positive)
           FILTER (WHERE total_reviews >= 50)                          AS mediana_pct_positivo
FROM core.v_game_latest
WHERE is_indie
  AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
  AND tramo_precio IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- 4.3 ¿Más reseñas compensan un precio menor? Índice de ingresos
-- reseñas × precio de lista. NO son dólares: es un índice relativo para comparar
-- tramos (las reseñas son un proxy de ventas). Excluye juegos gratuitos.
SELECT tramo_precio,
       count(*)                                                                      AS indies,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY total_reviews * list_price_usd)  AS mediana_indice,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY total_reviews * list_price_usd)  AS p90_indice,
       round(100.0 * sum(total_reviews * list_price_usd)
             / sum(sum(total_reviews * list_price_usd)) OVER (), 1)                 AS pct_del_total
FROM core.v_game_latest
WHERE is_indie
  AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
  AND tramo_precio IS NOT NULL
  AND tramo_precio <> '0. Gratis'
GROUP BY 1
ORDER BY 1;

-- 4.4 Evolución del precio de los indies de pago por año de lanzamiento
SELECT extract(year FROM release_date)::int                                AS anio,
       count(*)                                                            AS indies,
       round(100.0 * avg((tramo_precio = '0. Gratis')::int), 1)            AS pct_gratis,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY list_price_usd)
           FILTER (WHERE tramo_precio <> '0. Gratis')                      AS mediana_precio_pago
FROM core.v_game_latest
WHERE is_indie
  AND release_date BETWEEN '2016-01-01' AND '2023-12-31'
  AND tramo_precio IS NOT NULL
GROUP BY 1
ORDER BY 1;
