-- =====================================================================
-- 02_transform.sql — staging.games_raw  ->  modelo estrella en core
-- Reconstruye core por completo en cada ejecución (idempotente).
-- Los atributos del juego salen del snapshot más reciente;
-- las métricas se conservan para todos los snapshots.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 0. Dimensión fecha (solo la primera vez)
-- ---------------------------------------------------------------------
INSERT INTO core.dim_date
SELECT to_char(d, 'YYYYMMDD')::int,
       d::date,
       extract(year    FROM d)::smallint,
       extract(quarter FROM d)::smallint,
       extract(month   FROM d)::smallint,
       btrim(to_char(d, 'Month')),
       extract(week    FROM d)::smallint,
       extract(isodow  FROM d)::smallint,
       btrim(to_char(d, 'Day')),
       extract(isodow  FROM d) IN (6, 7)
FROM generate_series('1997-01-01'::date, '2030-12-31'::date, interval '1 day') AS d
ON CONFLICT (date_key) DO NOTHING;

-- ---------------------------------------------------------------------
-- 1. Limpiar core (las dimensiones de nombres se reconstruyen)
-- ---------------------------------------------------------------------
TRUNCATE core.fact_game_snapshot,
         core.bridge_game_developer, core.bridge_game_publisher,
         core.bridge_game_genre, core.bridge_game_category, core.bridge_game_tag,
         core.dim_game,
         core.dim_developer, core.dim_publisher, core.dim_genre,
         core.dim_category, core.dim_tag
RESTART IDENTITY;

-- Snapshot más reciente de cada juego
CREATE TEMP TABLE latest ON COMMIT DROP AS
SELECT DISTINCT ON (app_id) app_id, payload AS p
FROM staging.games_raw
ORDER BY app_id, snapshot_date DESC, loaded_at DESC;

-- Función local: convierte un campo JSON (arreglo o texto separado por comas)
-- en filas de texto limpias.
CREATE OR REPLACE FUNCTION pg_temp.json_list(j JSONB)
RETURNS SETOF TEXT LANGUAGE sql IMMUTABLE AS $$
    SELECT DISTINCT btrim(x)
    FROM (
        SELECT jsonb_array_elements_text(j) AS x WHERE jsonb_typeof(j) = 'array'
        UNION ALL
        SELECT regexp_split_to_table(j #>> '{}', ',') WHERE jsonb_typeof(j) = 'string'
    ) s
    WHERE btrim(x) <> '';
$$;

-- Fecha de lanzamiento como texto. Acepta los dos formatos del dataset:
--   "release_date": {"coming_soon": false, "date": "Oct 21, 2008"}   (versiones antiguas)
--   "release_date": "Oct 21, 2008"                                     (versiones recientes)
CREATE OR REPLACE FUNCTION pg_temp.release_text(p JSONB)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(p->'release_date')
               WHEN 'object' THEN p->'release_date'->>'date'
               WHEN 'string' THEN p->>'release_date'
           END;
$$;

-- ---------------------------------------------------------------------
-- 2. dim_game
-- ---------------------------------------------------------------------
INSERT INTO core.dim_game
SELECT l.app_id,
       NULLIF(btrim(p->>'name'), ''),
       core.parse_steam_date(pg_temp.release_text(p)),
       pg_temp.release_text(p),
       NULL,                                          -- release_date_key (se llena abajo)
       (p->'release_date'->>'coming_soon')::boolean,      -- NULL si el formato es texto
       (p->>'is_free')::boolean,
       (p->>'required_age')::numeric::smallint,
       (p->>'windows')::boolean,
       (p->>'mac')::boolean,
       (p->>'linux')::boolean,
       (SELECT count(*) FROM pg_temp.json_list(p->'supported_languages'))::smallint,
       (p->>'achievements')::numeric::int,
       CASE WHEN jsonb_typeof(p->'screenshots') = 'array' THEN jsonb_array_length(p->'screenshots') END,
       CASE WHEN jsonb_typeof(p->'movies')      = 'array' THEN jsonb_array_length(p->'movies') END,
       COALESCE(btrim(p->>'website'), '') <> '',
       EXISTS (SELECT 1 FROM pg_temp.json_list(p->'genres') g WHERE lower(g) = 'indie'),
       (jsonb_typeof(p->'tags') = 'object' AND p->'tags' ? 'Indie'),
       EXISTS (SELECT 1 FROM pg_temp.json_list(p->'genres') g WHERE lower(g) = 'early access')
FROM latest l;

UPDATE core.dim_game
SET release_date_key = to_char(release_date, 'YYYYMMDD')::int
WHERE release_date BETWEEN '1997-01-01' AND '2030-12-31';

-- ---------------------------------------------------------------------
-- 3. Dimensiones de nombres + tablas puente
-- ---------------------------------------------------------------------
-- Desarrolladores
INSERT INTO core.dim_developer (name)
SELECT DISTINCT v FROM latest, pg_temp.json_list(p->'developers') v;
INSERT INTO core.bridge_game_developer
SELECT DISTINCT l.app_id, d.developer_id
FROM latest l, pg_temp.json_list(l.p->'developers') v
JOIN core.dim_developer d ON d.name = v;

-- Publishers
INSERT INTO core.dim_publisher (name)
SELECT DISTINCT v FROM latest, pg_temp.json_list(p->'publishers') v;
INSERT INTO core.bridge_game_publisher
SELECT DISTINCT l.app_id, d.publisher_id
FROM latest l, pg_temp.json_list(l.p->'publishers') v
JOIN core.dim_publisher d ON d.name = v;

-- Géneros
INSERT INTO core.dim_genre (name)
SELECT DISTINCT v FROM latest, pg_temp.json_list(p->'genres') v;
INSERT INTO core.bridge_game_genre
SELECT DISTINCT l.app_id, d.genre_id
FROM latest l, pg_temp.json_list(l.p->'genres') v
JOIN core.dim_genre d ON d.name = v;

-- Categorías (Single-player, Steam Achievements, ...)
INSERT INTO core.dim_category (name)
SELECT DISTINCT v FROM latest, pg_temp.json_list(p->'categories') v;
INSERT INTO core.bridge_game_category
SELECT DISTINCT l.app_id, d.category_id
FROM latest l, pg_temp.json_list(l.p->'categories') v
JOIN core.dim_category d ON d.name = v;

-- Tags (objeto {"Tag": votos}) con su posición dentro del juego
INSERT INTO core.dim_tag (name)
SELECT DISTINCT btrim(t.key)
FROM latest l, jsonb_each(l.p->'tags') t
WHERE jsonb_typeof(l.p->'tags') = 'object' AND btrim(t.key) <> '';

INSERT INTO core.bridge_game_tag
SELECT l.app_id, d.tag_id, t.votes,
       row_number() OVER (PARTITION BY l.app_id ORDER BY t.votes DESC, d.name)::smallint
FROM latest l
CROSS JOIN LATERAL (
    SELECT btrim(key) AS name, value::numeric::int AS votes
    FROM jsonb_each(l.p->'tags')
    WHERE jsonb_typeof(l.p->'tags') = 'object'
) t
JOIN core.dim_tag d ON d.name = t.name;

-- ---------------------------------------------------------------------
-- 4. Hechos: un registro por juego y snapshot
-- ---------------------------------------------------------------------
INSERT INTO core.fact_game_snapshot (
    app_id, source, snapshot_date, price_usd, positive, negative,
    owners_low, owners_high, peak_ccu, recommendations, metacritic_score,
    avg_playtime_forever_min, median_playtime_forever_min)
SELECT r.app_id, r.source, r.snapshot_date,
       (r.payload->>'price')::numeric,
       (r.payload->>'positive')::numeric::int,
       (r.payload->>'negative')::numeric::int,
       NULLIF(regexp_replace(split_part(r.payload->>'estimated_owners', '-', 1), '\D', '', 'g'), '')::int,
       NULLIF(regexp_replace(split_part(r.payload->>'estimated_owners', '-', 2), '\D', '', 'g'), '')::int,
       (r.payload->>'peak_ccu')::numeric::int,
       (r.payload->>'recommendations')::numeric::int,
       NULLIF((r.payload->>'metacritic_score')::numeric::int, 0)::smallint,   -- 0 = sin dato
       (r.payload->>'average_playtime_forever')::numeric::int,
       (r.payload->>'median_playtime_forever')::numeric::int
FROM staging.games_raw r;

COMMIT;

-- ---------------------------------------------------------------------
-- 5. Vista de trabajo: juego + métricas del snapshot más reciente
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW core.v_game_latest AS
SELECT g.*,
       f.source, f.snapshot_date, f.price_usd, f.positive, f.negative,
       f.total_reviews, f.pct_positive, f.owners_low, f.owners_high,
       f.peak_ccu, f.recommendations, f.metacritic_score,
       f.avg_playtime_forever_min, f.median_playtime_forever_min
FROM core.dim_game g
JOIN LATERAL (
    SELECT * FROM core.fact_game_snapshot fs
    WHERE fs.app_id = g.app_id
    ORDER BY fs.snapshot_date DESC
    LIMIT 1
) f ON TRUE;
