CREATE OR REPLACE TABLE `your-project-id.crypto_analytics.FCT_PRICES` AS
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
    FROM `your-project-id.crypto_analytics.raw_crypto_prices`
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
