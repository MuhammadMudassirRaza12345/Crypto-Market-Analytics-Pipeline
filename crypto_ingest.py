import requests
import yaml
import json
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timezone

# ---- CONFIG ----
PROJECT_ID = "enduring-badge-425117-c9"
DATASET = "crypto_analytics"
TABLE = "raw_crypto_prices"
# DATASET_LOCATION = "US"   # change to match your GCP region if needed
COINS = "bitcoin,ethereum,solana,cardano,dogecoin,ripple,polkadot,litecoin,chainlink,avalanche-2"

def load_credentials(env_file=".env.yaml"):
    with open(env_file, "r") as f:
        config = yaml.safe_load(f)
    
    creds_dict = json.loads(config["PATH_CREDS_SERVICE_ACCOUNT"])
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    return credentials

def ensure_dataset_exists(client, dataset_id):
    """Create the dataset if it doesn't already exist."""
    dataset_ref = f"{PROJECT_ID}.{dataset_id}"
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset '{dataset_id}' already exists.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        # dataset.location = DATASET_LOCATION
        client.create_dataset(dataset, exists_ok=True)
        print(f"Dataset '{dataset_id}'.")

def fetch_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": COINS,
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def transform_data(raw_data):
    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for coin in raw_data:
        rows.append({
            "coin_id": coin.get("id"),
            "coin_name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "price_usd": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "volume_24h": coin.get("total_volume"),
            "price_change_24h": coin.get("price_change_percentage_24h"),
            "fetched_at": fetched_at
          
            
        })
    return rows

def load_to_bigquery(rows, credentials):
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

    # Make sure the dataset exists before we try to load into a table inside it
    ensure_dataset_exists(client, DATASET)

    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=[
            bigquery.SchemaField("coin_id", "STRING"),
            bigquery.SchemaField("coin_name", "STRING"),
            bigquery.SchemaField("symbol", "STRING"),
            bigquery.SchemaField("price_usd", "FLOAT64"),
            bigquery.SchemaField("market_cap", "FLOAT64"),
            bigquery.SchemaField("market_cap_rank", "INT64"),
            bigquery.SchemaField("volume_24h", "FLOAT64"),
            bigquery.SchemaField("price_change_24h", "FLOAT64"),
            bigquery.SchemaField("fetched_at", "TIMESTAMP"),
        ],
    )

    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()  # wait for job to complete

    print(f"Loaded {len(rows)} rows successfully via batch load.")

if __name__ == "__main__":
    credentials = load_credentials(".env.yaml")
    raw = fetch_crypto_data()
    rows = transform_data(raw)
    load_to_bigquery(rows, credentials)