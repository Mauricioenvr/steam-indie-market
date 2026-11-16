-- =====================================================================
-- Dataset base de los modelos de regresión: una fila por juego.
-- Universo: indies publicados 2016–2023, sin software, con precio de lista.
-- Se excluyen las fechas que solo traen mes y año: no tienen día de la semana.
-- Los géneros y los tags se leen aparte (formato largo) y se pivotean en Python.
-- =====================================================================
SELECT g.app_id,
       g.name,
       g.total_reviews,
       g.pct_positive,
       g.tramo_precio,
       g.list_price_usd,
       extract(year FROM g.release_date)::int  AS anio,
       d.month                                  AS mes,
       d.day_of_week                            AS dia_semana,
       g.is_early_access,
       g.n_languages,
       g.n_audio_languages,
       g.mac,
       g.linux,
       g.achievements,
       g.n_screenshots,
       g.n_movies,
       g.has_website,
       g.dlc_count,
       -- Autopublicado: no tiene publisher, o todos sus publishers son también desarrolladores
       NOT EXISTS (
           SELECT 1
           FROM core.bridge_game_publisher bp
           JOIN core.dim_publisher p USING (publisher_id)
           WHERE bp.app_id = g.app_id
             AND p.name NOT IN (
                 SELECT dv.name
                 FROM core.bridge_game_developer bd
                 JOIN core.dim_developer dv USING (developer_id)
                 WHERE bd.app_id = g.app_id)
       )                                        AS autopublicado,
       EXISTS (SELECT 1 FROM core.bridge_game_tag bt WHERE bt.app_id = g.app_id) AS tiene_tags
FROM core.v_game_latest g
JOIN core.dim_date d ON d.date_key = g.release_date_key
WHERE g.is_indie
  AND g.release_date BETWEEN '2016-01-01' AND '2023-12-31'
  AND g.tramo_precio IS NOT NULL
  AND g.release_date_raw !~ '^[A-Za-z]{3,9} \d{4}$';
