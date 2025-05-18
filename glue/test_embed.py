#!/usr/bin/env python
"""
Embed Parquet records from S3 and bulk-index into Amazon OpenSearch Serverless.
Save as glue/embed_index_opensearch.py and simply run:  python glue/embed_index_opensearch.py
"""

import os, time, json
from pathlib import Path
from typing import List

import pyarrow.dataset as ds
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers

from langchain_aws import BedrockEmbeddings

# -------------------------------------------------------------
# 0.  Config
# -------------------------------------------------------------
load_dotenv()                            # read ../.env

BUCKET_NAME        = os.getenv("BUCKET_NAME")
INPUT_KEY          = os.getenv("INPUT_KEY")
AWS_REGION         = os.getenv("AWS_REGION", "eu-west-2")
OPENSEARCH_ENDPOINT= os.getenv("OPENSEARCH_ENDPOINT")
INDEX_NAME         = os.getenv("INDEX_NAME", "products-embeddings")
ROWS               = int(os.getenv("ROWS", "1000"))
BATCH_SIZE         = int(os.getenv("BATCH_SIZE", "100"))

assert BUCKET_NAME and OPENSEARCH_ENDPOINT, "BUCKET_NAME & OPENSEARCH_ENDPOINT required"

# -------------------------------------------------------------
# 1.  Utilities
# -------------------------------------------------------------
def init_opensearch() -> OpenSearch:
    """Create a signed OpenSearch client (Serverless – service='aoss')."""
    ak, sk = os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"]
    st     = os.getenv("AWS_SESSION_TOKEN")
    auth   = AWS4Auth(ak, sk, AWS_REGION, "aoss", session_token=st)

    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        headers={"X-Amz-Content-Sha256": "UNSIGNED-PAYLOAD"},
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60,
    )

def ensure_index(client: OpenSearch, dim: int = 1024) -> None:
    """Create the index with a knn_vector mapping if it doesn't exist."""
    if client.indices.exists(INDEX_NAME):
        return
    body = {
        "settings": { "index": { "knn": True }},
        "mappings": {
            "properties": {
                "vector": { "type": "knn_vector", "dimension": dim },
                "text":   { "type": "text"         },
                "id":     { "type": "keyword"      }
            }
        }
    }
    client.indices.create(INDEX_NAME, body=body)
    print(f"Created index {INDEX_NAME} with k-NN mapping.")

def load_dataframe(n_rows: int) -> pd.DataFrame:
    """Read up to n_rows rows from parquet data on S3 into pandas."""
    ds_obj = ds.dataset(f"s3://{BUCKET_NAME}/{INPUT_KEY}",
                        format="parquet", partitioning="hive")
    table  = ds_obj.to_table().slice(0, n_rows)
    df = table.to_pandas()
    # Ensure all relevant columns exist
    for col in ["barcode", "name", "brands", "categories", "allergens", "energy_kcal_per_100g",
                "fat_per_100g", "sugars_per_100g", "proteins_per_100g", "ingredient_name", "ingredient_pct"]:
        if col not in df.columns:
            df[col] = ""
    # Convert numeric columns to string for concatenation
    for col in ["energy_kcal_per_100g", "fat_per_100g", "sugars_per_100g", "proteins_per_100g", "ingredient_pct"]:
        df[col] = df[col].fillna("").astype(str)
    # Build a single text blob including all fields
    df["text"] = (
        "Barcode: "        + df["barcode"]        + "; " +
        "Name: "           + df["name"]           + "; " +
        "Brands: "         + df["brands"]         + "; " +
        "Categories: "     + df["categories"]     + "; " +
        "Allergens: "      + df["allergens"]      + "; " +
        "Energy(kcal/100g): " + df["energy_kcal_per_100g"] + "; " +
        "Fat(g/100g): "    + df["fat_per_100g"]    + "; " +
        "Sugars(g/100g): " + df["sugars_per_100g"] + "; " +
        "Proteins(g/100g): "+ df["proteins_per_100g"] + "; " +
        "Ingredient: "     + df["ingredient_name"] + " (" + df["ingredient_pct"] + "%)"
    )
    return df[["id", "text"]]

def safe_embed(emb, text: str, retries=5, backoff=4) -> List[float]:
    """Embed text with exponential-backoff retries."""
    for i in range(retries):
        try:
            return emb.embed_query(text[:500])  # Titan limit guard
        except Exception as e:
            print(f"[embed retry {i+1}/{retries}] {e}")
            time.sleep(backoff * 2**i)
    raise RuntimeError("Embedding failed after retries")

# -------------------------------------------------------------
# 2.  Main driver
# -------------------------------------------------------------
def main():
    df   = load_dataframe(ROWS)

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
    client     = init_opensearch()
    ensure_index(client)

    actions = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Embedding"):
        vec = safe_embed(embeddings, row["text"])
        actions.append({
            "_index": INDEX_NAME,
            "_source":{
               "id":   str(row["id"]),
               "text": row["text"],
               "vector": vec
            }
        })

    # Bulk upload
    success, _ = helpers.bulk(client, actions, chunk_size=BATCH_SIZE, request_timeout=90)
    failed = len(actions) - success
    print(f"✅ Upload results: {success} succeeded, {failed} failed")

if __name__ == "__main__":
    main()