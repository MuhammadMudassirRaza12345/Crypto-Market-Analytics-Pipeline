CREATE OR REPLACE TABLE `your-project-id.crypto_analytics.DIM_DATE` AS
SELECT DISTINCT
    DATE(fetched_at) AS full_date,
    EXTRACT(YEAR FROM fetched_at) AS year,
    EXTRACT(MONTH FROM fetched_at) AS month,
    EXTRACT(DAY FROM fetched_at) AS day
FROM `your-project-id.crypto_analytics.raw_crypto_prices`;
