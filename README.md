# Crypto Market Analytics Pipeline

An end-to-end data engineering project that extracts live cryptocurrency market data from a public API, models it into a star schema in BigQuery, tracks historical rank changes using SCD Type 2, and visualizes it in an interactive Looker Studio dashboard.

## Architecture

```
CoinGecko API (public, no auth)
      │
      ▼
Python script (requests + service account auth)
      │
      ▼
BigQuery — raw_crypto_prices (raw landing table)
      │
      ▼
SQL Transformation Layer
   ├── ROW_NUMBER() → dedup to latest snapshot per coin/day
   ├── Star Schema  → FCT_PRICES, DIM_COIN, DIM_DATE
   └── LAG() / LEAD() → SCD Type 2 (DIM_COIN_HISTORY) for rank tracking
      │
      ▼
Looker Studio Dashboard
   ├── Price trend (time series, by coin)
   ├── Market cap comparison (bar chart)
   ├── Top gainers/losers (table)
   ├── Total market cap (scorecard)
   └── Dynamic date dropdown control
```

## Tech Stack

- **Extraction:** Python, `requests`, CoinGecko public API
- **Storage/Warehouse:** Google BigQuery
- **Authentication:** GCP Service Account (via `.env.yaml`)
- **Modeling:** SQL — window functions (`ROW_NUMBER`, `LAG`, `LEAD`), star schema, SCD Type 2
- **Visualization:** Looker Studio

## Data Modeling Details

### 1. Deduplication with `ROW_NUMBER()`
Raw data can be ingested multiple times per day. A partitioned `ROW_NUMBER()` over `coin_id` + date keeps only the latest snapshot per coin per day:

```sql
ROW_NUMBER() OVER (
    PARTITION BY coin_id, DATE(fetched_at)
    ORDER BY fetched_at DESC
) AS rn
```

### 2. Star Schema
- **FCT_PRICES** — fact table with measures: `price_usd`, `market_cap`, `volume_24h`, `price_change_24h`, `market_cap_rank`
- **DIM_COIN** — descriptive attributes: `coin_id`, `coin_name`, `symbol`
- **DIM_DATE** — calendar attributes: `full_date`, `year`, `month`, `day`

### 3. Slowly Changing Dimension (Type 2)
Tracks historical changes in a coin's `market_cap_rank` over time using `LAG()`/`LEAD()`, preserving `valid_from`, `valid_to`, and `is_current` for full historical trail — rather than overwriting the rank on every load.

## Dashboard Features

- **Time series chart** — price trend per coin across dates
- **Bar chart** — market cap comparison across coins
- **Table** — top gainers/losers sorted by 24h price change, with market cap rank
- **Scorecard** — total market cap
- **Dropdown date control** — lets users view any historical snapshot, not just the latest, without hardcoding a date filter

## Project Files

```
crypto-analytics-pipeline/
├── crypto_ingest.py          # API extraction + BigQuery load
├── sql/
│   ├── 01_dim_coin.sql
│   ├── 02_dim_date.sql
│   ├── 03_fct_prices.sql
│   └── 04_dim_coin_history_scd2.sql
└── README.md
```

## Key Engineering Decisions

- **Batch load over streaming insert:** Used `load_table_from_json` instead of `insert_rows_json` since streaming inserts require a billing-enabled project; batch loads work on the free tier and suit a periodic ingestion pattern.
- **Dynamic "latest" handling:** Rather than hardcoding a date filter for current-state views, the dashboard uses a date dropdown control so it stays correct as new data lands — no manual updates required.
