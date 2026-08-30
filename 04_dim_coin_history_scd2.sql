-- SCD Type 2: tracks historical market_cap_rank changes per coin
-- using LAG (look back) to detect a change, and LEAD (look forward)
-- to derive the validity window (valid_from / valid_to / is_current)

CREATE OR REPLACE TABLE `your-project-id.crypto_analytics.DIM_COIN_HISTORY` AS
WITH rank_changes AS (
    SELECT
        coin_id,
        market_cap_rank,
        full_date,
        LAG(market_cap_rank) OVER (
            PARTITION BY coin_id ORDER BY full_date
        ) AS prev_rank
    FROM `your-project-id.crypto_analytics.FCT_PRICES`
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
