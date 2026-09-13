CREATE OR REPLACE TABLE `enduring-badge-425117-c9.crypto_analytics.DIM_COIN` AS
SELECT DISTINCT
    coin_id,
    coin_name,
    symbol
FROM `enduring-badge-425117-c9.crypto_analytics.raw_crypto_prices`;

CREATE OR REPLACE TABLE `enduring-badge-425117-c9.crypto_analytics.DIM_DATE` AS
SELECT DISTINCT
    DATE(fetched_at) AS full_date,
    EXTRACT(YEAR FROM fetched_at) AS year,
    EXTRACT(MONTH FROM fetched_at) AS month,
    EXTRACT(DAY FROM fetched_at) AS day
FROM `enduring-badge-425117-c9.crypto_analytics.raw_crypto_prices`;

CREATE OR REPLACE TABLE `enduring-badge-425117-c9.crypto_analytics.FCT_PRICES` AS
WITH ranked AS (
    SELECT
        coin_id,
        price_usd,
        market_cap,
        market_cap_rank,
        volume_24h,
        price_change_24h,
        fetched_at,
        DATE(fetched_at) AS full_date,
        ROW_NUMBER() OVER (
            PARTITION BY coin_id, DATE(fetched_at)
            ORDER BY fetched_at DESC
        ) AS rn
    FROM `enduring-badge-425117-c9.crypto_analytics.raw_crypto_prices`
)
SELECT
    coin_id,
    full_date,
    price_usd,
    market_cap,
    market_cap_rank,
    volume_24h,
    price_change_24h
FROM ranked
WHERE rn = 1;

-- SCD Type 2: tracks historical market_cap_rank changes per coin
-- using LAG (look back) to detect a change, and LEAD (look forward)
-- to derive the validity window (valid_from / valid_to / is_current)

CREATE OR REPLACE TABLE `enduring-badge-425117-c9.crypto_analytics.DIM_COIN_HISTORY` AS
WITH rank_changes AS (
    SELECT
        coin_id,
        market_cap_rank,
        full_date,
        LAG(market_cap_rank) OVER (
            PARTITION BY coin_id ORDER BY full_date
        ) AS prev_rank
    FROM `enduring-badge-425117-c9.crypto_analytics.FCT_PRICES`
)
SELECT
    coin_id,
    market_cap_rank,
    full_date AS valid_from,
    LEAD(full_date) OVER (
        PARTITION BY coin_id ORDER BY full_date
    ) AS valid_to,
    CASE WHEN LEAD(full_date) OVER (
        PARTITION BY coin_id ORDER BY full_date
    ) IS NULL THEN TRUE ELSE FALSE END AS is_current
FROM rank_changes
WHERE prev_rank IS NULL OR prev_rank != market_cap_rank;

-- NEW (not in v1): a compact summary view that feeds the LLM layer.
-- Combines latest prices with 24h change AND any rank movements
-- pulled from the SCD2 history table — so the LLM commentary can
-- mention rank shifts, not just price moves.

CREATE OR REPLACE VIEW `enduring-badge-425117-c9.crypto_analytics.VW_DAILY_SUMMARY` AS
SELECT
    f.coin_id,
    c.coin_name,
    c.symbol,
    f.full_date,
    f.price_usd,
    f.market_cap,
    f.market_cap_rank,
    f.price_change_24h,
    h.valid_from AS rank_changed_on,
    LAG(h.market_cap_rank) OVER (
        PARTITION BY h.coin_id ORDER BY h.valid_from
    ) AS previous_rank
FROM `enduring-badge-425117-c9.crypto_analytics.FCT_PRICES` f
JOIN `enduring-badge-425117-c9.crypto_analytics.DIM_COIN` c USING (coin_id)
LEFT JOIN `enduring-badge-425117-c9.crypto_analytics.DIM_COIN_HISTORY` h
    ON h.coin_id = f.coin_id AND h.is_current = TRUE
WHERE f.full_date = (SELECT MAX(full_date) FROM `enduring-badge-425117-c9.crypto_analytics.FCT_PRICES`);

