"""
app.py
------------------
Streamlit dashboard for the crypto_analytics BigQuery data.

Replaces the old "insert commentary into BigQuery" flow — instead, everything
(charts, table, scorecard, AI summary) is rendered directly in the app.

Setup:
    pip install streamlit plotly pandas google-cloud-bigquery openai pyyaml

    .env.yaml must contain:
        PATH_CREDS_SERVICE_ACCOUNT: '{"type": "service_account", ...}'
        OPENAI_API_KEY: 'sk-proj-xxxxxxxx'

Usage:
    streamlit run app.py
"""

import json
import yaml
import pandas as pd
import streamlit as st
import plotly.express as px
from google.cloud import bigquery
from google.oauth2 import service_account
from openai import OpenAI

# ---------------- CONFIG ----------------
PROJECT_ID = "enduring-badge-425117-c9"
DATASET = "crypto_analytics"
TABLE = "raw_crypto_prices"
OPENAI_MODEL = "gpt-4o-mini"

st.set_page_config(page_title="Crypto Market Dashboard", layout="wide")

# ---------------- STYLING ----------------
st.markdown(
    """
    <style>
    /* App background */
    .stApp {
        background-color: gold;
    }

    /* Plotly chart containers */
    .stPlotlyChart {
        background-color: white;
        border-radius: 10px;
        padding: 8px;
    }

    /* Tables / dataframes */
    [data-testid="stDataFrame"] {
        background-color: white;
        border-radius: 10px;
    }

    /* Scorecard / metric */
    [data-testid="stMetric"] {
        background-color: white;
        border-radius: 10px;
        padding: 12px;
    }
    [data-testid="stMetricLabel"] {
        color: black;
    }
    [data-testid="stMetricValue"] {
        color: black;
    }

    /* Headings */
    h1, h2, h3 {
        color: white;
    }

    /* AI summary text */
    .summary-box {
        background-color: transparent;
        color: white !important;
        font-size: 17px;
        font-weight: 500;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- CREDENTIALS ----------------
@st.cache_resource
def load_credentials(env_file=".env.yaml"):
    with open(env_file, "r") as f:
        config = yaml.safe_load(f)
    creds_dict = json.loads(config["PATH_CREDS_SERVICE_ACCOUNT"])
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    return credentials, config.get("OPENAI_API_KEY")


credentials, openai_api_key = load_credentials()
bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials)


# ---------------- DATA LOADING ----------------
@st.cache_data(ttl=300)
def get_history() -> pd.DataFrame:
    query = f"""
        SELECT coin_id, coin_name, symbol, price_usd, market_cap,
               market_cap_rank, volume_24h, price_change_24h, fetched_at
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        ORDER BY fetched_at
    """
    df = bq_client.query(query).to_dataframe()
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    df["snapshot_date"] = df["fetched_at"].dt.date
    return df


# ---------------- AI COMMENTARY ----------------
def build_prompt(df: pd.DataFrame) -> str:
    cols = df[["coin_name", "symbol", "price_usd", "market_cap_rank", "price_change_24h"]]
    return f"""You are a crypto market analyst. Below is today's market summary
(price, 24h change, market cap rank). Write a short newsletter-style
commentary in 3-4 sentences. Explicitly mention any notable movers.

{cols.to_string(index=False)}
"""


def generate_commentary(prompt: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=400,
        messages=[
            {"role": "system", "content": "You are a concise crypto market analyst who writes short newsletter-style commentary."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


# ---------------- APP ----------------
st.title("📊 Crypto Market Dashboard")

history_df = get_history()

if history_df.empty:
    st.warning("No data found in raw_crypto_prices yet.")
    st.stop()

available_dates = sorted(history_df["snapshot_date"].unique(), reverse=True)

# Dropdown date control — lets user pick any historical snapshot
selected_date = st.selectbox("Select snapshot date", available_dates, index=0)

snapshot_df = history_df[history_df["snapshot_date"] == selected_date].sort_values(
    "market_cap_rank"
)

# ---- Scorecard: total market cap ----
total_market_cap = snapshot_df["market_cap"].sum()
st.metric(label=f"Total Market Cap — {selected_date}", value=f"${total_market_cap:,.0f}")

col1, col2 = st.columns(2)

# ---- Time series chart: price trend per coin across dates ----
with col1:
    st.subheader("Price Trend per Coin")
    fig_line = px.line(
        history_df,
        x="fetched_at",
        y="price_usd",
        color="coin_name",
        template="plotly_white",
    )
    fig_line.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig_line, use_container_width=True)

# ---- Bar chart: market cap comparison (selected snapshot) ----
with col2:
    st.subheader(f"Market Cap Comparison — {selected_date}")
    fig_bar = px.bar(
        snapshot_df.sort_values("market_cap", ascending=False),
        x="coin_name",
        y="market_cap",
        template="plotly_white",
    )
    fig_bar.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig_bar, use_container_width=True)

# ---- Table: top gainers/losers sorted by 24h change ----
st.subheader("Top Gainers / Losers (24h)")
table_df = snapshot_df[
    ["coin_name", "symbol", "price_usd", "price_change_24h", "market_cap_rank"]
].sort_values("price_change_24h", ascending=False)
st.dataframe(table_df, use_container_width=True)

# ---- AI-generated commentary (printed in-app, not inserted into BigQuery) ----
st.subheader("AI-Generated Market Commentary")
if openai_api_key:
    prompt = build_prompt(snapshot_df)
    commentary = generate_commentary(prompt, openai_api_key)
    st.markdown(f'<div class="summary-box">{commentary}</div>', unsafe_allow_html=True)
else:
    st.info("Add OPENAI_API_KEY to .env.yaml to enable AI commentary.")