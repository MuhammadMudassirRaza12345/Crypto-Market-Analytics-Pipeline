-- NEW (not in v1): a compact summary view that feeds the LLM layer.
-- Combines latest prices with 24h change AND any rank movements
-- pulled from the SCD2 history table — so the LLM commentary can
-- mention rank shifts, not just price moves.

CREATE OR REPLACE VIEW `your-project-id.crypto_analytics.VW_DAILY_SUMMARY` AS
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
FROM `your-project-id.crypto_analytics.FCT_PRICES` f
JOIN `your-project-id.crypto_analytics.DIM_COIN` c USING (coin_id)
LEFT JOIN `your-project-id.crypto_analytics.DIM_COIN_HISTORY` h
    ON h.coin_id = f.coin_id AND h.is_current = TRUE
WHERE f.full_date = (SELECT MAX(full_date) FROM `your-project-id.crypto_analytics.FCT_PRICES`);
