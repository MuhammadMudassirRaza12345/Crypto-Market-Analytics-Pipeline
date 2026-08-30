CREATE OR REPLACE TABLE `your-project-id.crypto_analytics.DIM_COIN` AS
SELECT DISTINCT
    coin_id,
    coin_name,
    symbol
FROM `your-project-id.crypto_analytics.raw_crypto_prices`;
