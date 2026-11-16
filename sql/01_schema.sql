-- =====================================================================
-- 01_schema.sql — Esquema del proyecto
--   staging : datos crudos tal como llegan (JSONB)
--   core    : modelo estrella (dimensiones, tablas puente, hechos)
-- Es idempotente: se puede ejecutar varias veces sin error.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

-- ---------------------------------------------------------------------
-- STAGING
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.games_raw (
    app_id        INTEGER      NOT NULL,
    source        TEXT         NOT NULL,          -- 'kaggle_fronkon', 'steam_api', ...
    snapshot_date DATE         NOT NULL,          -- fecha a la que corresponden los datos
    payload       JSONB        NOT NULL,
    loaded_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (app_id, source, snapshot_date)
);

-- ---------------------------------------------------------------------
-- FUNCIONES AUXILIARES
-- ---------------------------------------------------------------------

-- Convierte fechas de Steam ('Oct 21, 2008', '21 Oct, 2008', 'Oct 2008')
-- a DATE. Devuelve NULL si no se puede interpretar ('Coming soon', 'TBA'...).
CREATE OR REPLACE FUNCTION core.parse_steam_date(txt TEXT)
RETURNS DATE
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    t TEXT := btrim(txt);
BEGIN
    IF t IS NULL OR t = '' THEN
        RETURN NULL;
    END IF;
    IF t ~ '^\d{4}-\d{2}-\d{2}' THEN
        RETURN left(t, 10)::date;               -- ISO: '2008-10-21'
    ELSIF t ~ '^[A-Za-z]{3,9} \d{1,2}, \d{4}$' THEN
        RETURN to_date(t, 'Mon DD, YYYY');
    ELSIF t ~ '^\d{1,2} [A-Za-z]{3,9}, \d{4}$' THEN
        RETURN to_date(t, 'DD Mon, YYYY');
    ELSIF t ~ '^[A-Za-z]{3,9} \d{4}$' THEN
        RETURN to_date(t, 'Mon YYYY');          -- se asume día 1
    END IF;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$;

-- ---------------------------------------------------------------------
-- DIMENSIONES
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.dim_date (
    date_key     INTEGER PRIMARY KEY,             -- YYYYMMDD
    full_date    DATE    NOT NULL UNIQUE,
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,
    month        SMALLINT NOT NULL,
    month_name   TEXT     NOT NULL,
    iso_week     SMALLINT NOT NULL,
    day_of_week  SMALLINT NOT NULL,               -- 1 = lunes ... 7 = domingo
    day_name     TEXT     NOT NULL,
    is_weekend   BOOLEAN  NOT NULL
);

CREATE TABLE IF NOT EXISTS core.dim_game (
    app_id            INTEGER PRIMARY KEY,
    name              TEXT,
    release_date      DATE,
    release_date_raw  TEXT,                       -- texto original, para auditar
    release_date_key  INTEGER REFERENCES core.dim_date(date_key),
    coming_soon       BOOLEAN,
    is_free           BOOLEAN,
    required_age      SMALLINT,
    windows           BOOLEAN,
    mac               BOOLEAN,
    linux             BOOLEAN,
    n_languages       SMALLINT,
    achievements      INTEGER,
    n_screenshots     SMALLINT,
    n_movies          SMALLINT,
    has_website       BOOLEAN,
    is_indie_genre    BOOLEAN,                    -- 'Indie' como género (lo elige el desarrollador)
    is_indie_tag      BOOLEAN,                    -- 'Indie' como tag (lo vota la comunidad)
    is_early_access   BOOLEAN
);

CREATE TABLE IF NOT EXISTS core.dim_developer (developer_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS core.dim_publisher (publisher_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS core.dim_genre     (genre_id     SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS core.dim_category  (category_id  SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS core.dim_tag       (tag_id       SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);

-- ---------------------------------------------------------------------
-- TABLAS PUENTE (relaciones muchos a muchos)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.bridge_game_developer (
    app_id INTEGER REFERENCES core.dim_game(app_id) ON DELETE CASCADE,
    developer_id INTEGER REFERENCES core.dim_developer(developer_id),
    PRIMARY KEY (app_id, developer_id)
);
CREATE TABLE IF NOT EXISTS core.bridge_game_publisher (
    app_id INTEGER REFERENCES core.dim_game(app_id) ON DELETE CASCADE,
    publisher_id INTEGER REFERENCES core.dim_publisher(publisher_id),
    PRIMARY KEY (app_id, publisher_id)
);
CREATE TABLE IF NOT EXISTS core.bridge_game_genre (
    app_id INTEGER REFERENCES core.dim_game(app_id) ON DELETE CASCADE,
    genre_id INTEGER REFERENCES core.dim_genre(genre_id),
    PRIMARY KEY (app_id, genre_id)
);
CREATE TABLE IF NOT EXISTS core.bridge_game_category (
    app_id INTEGER REFERENCES core.dim_game(app_id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES core.dim_category(category_id),
    PRIMARY KEY (app_id, category_id)
);
CREATE TABLE IF NOT EXISTS core.bridge_game_tag (
    app_id   INTEGER REFERENCES core.dim_game(app_id) ON DELETE CASCADE,
    tag_id   INTEGER REFERENCES core.dim_tag(tag_id),
    votes    INTEGER,                             -- votos de la comunidad para ese tag
    tag_rank SMALLINT,                            -- 1 = tag más votado del juego
    PRIMARY KEY (app_id, tag_id)
);

-- ---------------------------------------------------------------------
-- HECHOS: métricas por juego y por snapshot
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.fact_game_snapshot (
    app_id                   INTEGER REFERENCES core.dim_game(app_id) ON DELETE CASCADE,
    source                   TEXT    NOT NULL,
    snapshot_date            DATE    NOT NULL,
    price_usd                NUMERIC(8,2),
    positive                 INTEGER,
    negative                 INTEGER,
    total_reviews            INTEGER GENERATED ALWAYS AS (positive + negative) STORED,
    pct_positive             NUMERIC(5,2) GENERATED ALWAYS AS (
                                 CASE WHEN positive + negative > 0
                                      THEN round(100.0 * positive / (positive + negative), 2)
                                 END) STORED,
    owners_low               INTEGER,
    owners_high              INTEGER,
    peak_ccu                 INTEGER,
    recommendations          INTEGER,
    metacritic_score         SMALLINT,
    avg_playtime_forever_min INTEGER,
    median_playtime_forever_min INTEGER,
    PRIMARY KEY (app_id, source, snapshot_date)
);

-- Columnas añadidas después de la primera versión (seguro en bases ya creadas)
ALTER TABLE core.dim_game           ADD COLUMN IF NOT EXISTS dlc_count         INTEGER;
ALTER TABLE core.dim_game           ADD COLUMN IF NOT EXISTS n_audio_languages SMALLINT;
ALTER TABLE core.fact_game_snapshot ADD COLUMN IF NOT EXISTS discount_pct      SMALLINT;
ALTER TABLE core.fact_game_snapshot ADD COLUMN IF NOT EXISTS list_price_usd    NUMERIC(8,2);
ALTER TABLE core.dim_game           ADD COLUMN IF NOT EXISTS is_software       BOOLEAN;

-- Reconstruye el precio de lista a partir del precio con descuento.
-- Dividir produce valores como 9.98; si el resultado está a 3 centavos o
-- menos de un precio terminado en .99, se ajusta a ese valor (9.98 -> 9.99).
CREATE OR REPLACE FUNCTION core.list_price(price NUMERIC, discount NUMERIC)
RETURNS NUMERIC
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN price IS NULL THEN NULL
        WHEN COALESCE(discount, 0) = 0 THEN price
        WHEN discount >= 100 THEN NULL                 -- 100 % de descuento: no recuperable
        ELSE (
            SELECT CASE WHEN ceil(raw) - 0.01 - raw BETWEEN 0 AND 0.03
                        THEN ceil(raw) - 0.01
                        ELSE round(raw, 2) END
            FROM (SELECT price / (1 - discount / 100.0) AS raw) r
        )
    END;
$$;

CREATE INDEX IF NOT EXISTS ix_fact_snapshot_date ON core.fact_game_snapshot (snapshot_date);
CREATE INDEX IF NOT EXISTS ix_game_release_key  ON core.dim_game (release_date_key);
CREATE INDEX IF NOT EXISTS ix_bridge_tag_tag    ON core.bridge_game_tag (tag_id);
CREATE INDEX IF NOT EXISTS ix_bridge_genre_genre ON core.bridge_game_genre (genre_id);
