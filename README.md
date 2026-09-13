<div align="center">

# 📊 Crypto Market Analytics Pipeline

**An end-to-end data engineering project** that extracts live cryptocurrency market data from a public API, models it into a star schema in BigQuery, tracks historical rank changes using SCD Type 2, and now layers on **AI-generated market commentary** and an **interactive Streamlit dashboard**.

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![BigQuery](https://img.shields.io/badge/Google%20BigQuery-Data%20Warehouse-4285F4?logo=googlecloud&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM%20Commentary-412991?logo=openai&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)

</div>

---

## 📑 Table of Contents

- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Data Modeling Details](#-data-modeling-details)
- [AI Commentary Layer](#-ai-commentary-layer)
- [Dashboards](#-dashboards)
- [Project Files](#-project-files)
- [Setup](#-setup)
- [Usage](#-usage)
- [Key Engineering Decisions](#-key-engineering-decisions)

---

## 🖼 Screenshots

<div align="center">

<img src="https://github.com/MuhammadMudassirRaza12345/Crypto-Market-Analytics-Pipeline/blob/main/s1.PNG" width="800" alt="Dashboard screenshot 1"/>

<br/><br/>

<img src="https://github.com/MuhammadMudassirRaza12345/Crypto-Market-Analytics-Pipeline/blob/main/s1.PNG" width="800" alt="Dashboard screenshot 2"/>

<br/><br/>

<img src="https://github.com/MuhammadMudassirRaza12345/Crypto-Market-Analytics-Pipeline/blob/main/s1.PNG" width="800" alt="Dashboard screenshot 3"/>

</div>

---

## 🏗 Architecture

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
VW_DAILY_SUMMARY (view)
   combines latest prices + 24h change + rank movement into one row per coin
      │
      ├──▶ 🤖 LLM Commentary Layer (OpenAI) ──▶ AI_COMMENTARY table
      │
      ├──▶ 📈 Looker Studio Dashboard
      │
      └──▶ 🖥️ Streamlit Dashboard (Plotly charts + AI summary, in one app)
```

---

## 🧰 Tech Stack

| Layer               | Tool / Service                                   |
|---------------------|---------------------------------------------------|
| Extraction          | Python, `requests`, CoinGecko public API          |
| Storage / Warehouse | Google BigQuery                                    |
| Authentication      | GCP Service Account (via `.env.yaml`)              |
| Modeling            | SQL — window functions (`ROW_NUMBER`, `LAG`, `LEAD`), star schema, SCD Type 2 |
| AI Commentary       | OpenAI API (`gpt-4o-mini`)                         |
| Dashboards          | Looker Studio **and** Streamlit + Plotly           |

---

## 🗃 Data Modeling Details

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

Tracks historical changes in a coin's `market_cap_rank` over time using `LAG()`/`LEAD()`, preserving `valid_from`, `valid_to`, and `is_current` for a full historical trail — rather than overwriting the rank on every load.

### 4. `VW_DAILY_SUMMARY` — the LLM-facing view

A compact view that feeds the LLM layer. It combines the latest prices and 24h change with any rank movement pulled from `DIM_COIN_HISTORY`, using `LAG()` to surface each coin's `previous_rank` alongside its current one:

```sql
CREATE OR REPLACE VIEW `your-project-id.crypto_analytics.VW_DAILY_SUMMARY` AS
SELECT
    f.coin_id, c.coin_name, c.symbol, f.full_date,
    f.price_usd, f.market_cap, f.market_cap_rank, f.price_change_24h,
    h.valid_from AS rank_changed_on,
    LAG(h.market_cap_rank) OVER (
        PARTITION BY h.coin_id ORDER BY h.valid_from
    ) AS previous_rank
FROM `your-project-id.crypto_analytics.FCT_PRICES` f
JOIN `your-project-id.crypto_analytics.DIM_COIN` c USING (coin_id)
LEFT JOIN `your-project-id.crypto_analytics.DIM_COIN_HISTORY` h
    ON h.coin_id = f.coin_id AND h.is_current = TRUE
WHERE f.full_date = (SELECT MAX(full_date) FROM `your-project-id.crypto_analytics.FCT_PRICES`);
```

This means downstream commentary can reference **rank shifts**, not just price moves.

---

## 🤖 AI Commentary Layer

`llm_insights.py` reads `VW_DAILY_SUMMARY`, builds a prompt summarizing the day's market, and asks OpenAI (`gpt-4o-mini` by default) to write a short, newsletter-style commentary — explicitly mentioning any rank changes.

The commentary is written to a BigQuery table (`AI_COMMENTARY`) using a **streaming insert** (`insert_rows_json`) rather than a DML `INSERT` query, so it works even on projects without billing enabled.

---

## 🖥 Dashboards

The project ships with two ways to view the data:

**Looker Studio** (original)
- Price trend (time series, by coin)
- Market cap comparison (bar chart)
- Top gainers/losers (table)
- Total market cap (scorecard)
- Dynamic date dropdown control

**Streamlit + Plotly (`app.py`)** — a self-contained alternative that adds the AI commentary directly into the same view:
- 📈 **Time series chart** — price trend per coin across dates
- 📊 **Bar chart** — market cap comparison across coins
- 📋 **Table** — top gainers/losers sorted by 24h price change, with market cap rank
- 🧮 **Scorecard** — total market cap
- 📅 **Date dropdown control** — browse any historical snapshot, not just the latest, without hardcoding a date filter
- 🤖 **AI-generated commentary** — rendered directly in the app, gold-and-white themed

---

## 📁 Project Files

```
crypto-analytics-pipeline/
├── crypto_ingest.py                 # API extraction + BigQuery load
├── 01_dim_coin.sql                  # Coin dimension
├── 02_dim_date.sql                  # Date dimension
├── 03_fct_prices.sql                # Fact table
├── 04_dim_coin_history_scd2.sql     # SCD Type 2 — rank history
├── 05_daily_market_summary.sql      # VW_DAILY_SUMMARY view (feeds the LLM layer)
├── llm_insights.py                  # Generates AI commentary from VW_DAILY_SUMMARY
├── app.py                           # Streamlit dashboard (charts + AI summary)
├── requirement.txt
├── .env.yaml                        # Service account creds + OpenAI key (not committed)
└── README.md
```

---

## ⚙️ Setup

1. **Install dependencies**
   ```bash
   pip install -r requirement.txt
    
   ```

2. **Configure credentials** — create `.env.yaml` in the project root (never commit this file):
   ```yaml
   PATH_CREDS_SERVICE_ACCOUNT: '{"type": "service_account", ...}'
   OPENAI_API_KEY: 'sk-proj-xxxxxxxx'
   ```

3. **Set your BigQuery project and dataset** — update `PROJECT_ID` and `DATASET` at the top of each script.

---

## ▶️ Usage

| Step | Command | What it does |
|------|---------|---------------|
| 1 | `python crypto_ingest.py` | Fetches CoinGecko prices, loads into `raw_crypto_prices` (auto-creates the dataset if needed) |
| 2 | Run `01`–`04` SQL scripts | Builds the star schema + SCD2 rank history |
| 3 | Run `05_daily_market_summary.sql` | Creates/refreshes `VW_DAILY_SUMMARY` |
| 4 | `python llm_insights.py` | Generates and saves the AI market commentary |
| 5 | `streamlit run app.py` | Launches the interactive dashboard |

---

## 🔑 Key Engineering Decisions

- **Batch load over streaming insert (raw ingestion):** `crypto_ingest.py` uses `load_table_from_json` instead of `insert_rows_json` for raw price data, since it suits a periodic ingestion pattern and works on the free tier.
- **Streaming insert for AI commentary:** `llm_insights.py` uses `insert_rows_json` instead of a DML `INSERT` query — DML requires a billing-enabled project, while streaming inserts don't.
- **Dynamic "latest" handling:** Rather than hardcoding a date filter for current-state views, both dashboards use a date dropdown control so they stay correct as new data lands — no manual updates required.
- **SCD Type 2 over overwrite:** Rank history is preserved with `valid_from` / `valid_to` / `is_current` rather than overwriting each coin's rank on every load, so rank *movement* — not just the current rank — is queryable.
