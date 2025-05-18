import os
import sys
import boto3
import pandas as pd
from langchain_aws import BedrockEmbeddings
from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection
from opensearchpy.helpers import bulk
import pyarrow.dataset as ds
from tqdm import tqdm
import argparse
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket_name", required=True)
    parser.add_argument("--input_key", default="clean_data/vectorised/")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--opensearch_endpoint", required=True)
    parser.add_argument("--collection_name", default="products-embeddings")

    args, _ = parser.parse_known_args()

    bucket_name        = args.bucket_name
    input_key          = args.input_key
    region             = args.region
    opensearch_endpoint= args.opensearch_endpoint
    collection_name    = args.collection_name

    # Read CSV from S3 into pandas DataFrame

    dataset = ds.dataset(
        f"s3://{bucket_name}/{input_key}",
        format="parquet",
        partitioning="hive"
    )
    table = dataset.to_table()
    df = table.to_pandas()
    print("Loaded", len(df), "records for embedding")
    # Fill missing fields
    df["product_name"]     = df["product_name"].fillna("")
    df["ingredients_text"] = df["ingredients_text"].fillna("")
    df["categories"]       = df["categories"].fillna("")
    df["doc_text"]         = (
        df["product_name"] + " "
        + df["ingredients_text"] + " "
        + df["categories"]
    )

    # Initialize Bedrock embeddings
    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0"
    )

    def safe_embed(text, retries=3, delay=2):
        for attempt in range(retries):
            try:
                return embeddings.embed_query(text)
            except Exception as e:
                print(f"[Retry {attempt+1}] Failed to embed: {e}")
                time.sleep(delay * (2 ** attempt))
        raise RuntimeError("Embedding failed after retries.")

    # Prepare documents for bulk indexing
    docs = []
    for _, row in df.iterrows():
        vector = safe_embed(row["doc_text"][:1000])
        docs.append({
            "_index":   collection_name,
            "_id":      str(row["id"]),
            "id":       str(row["id"]),
            "product_name":       row["product_name"],
            "sugars_100g":        row.get("sugars_100g"),
            "fat_100g":           row.get("fat_100g"),
            "proteins_100g":      row.get("proteins_100g"),
            "carbohydrates_100g": row.get("carbohydrates_100g"),
            "energy_kcal_100g":   row.get("energy_kcal_100g"),
            "categories":         row["categories"],
            "ingredients_text":   row["ingredients_text"],
            "vector":             vector
        })

    # Sign requests for OpenSearch Serverless
    session = boto3.Session()
    creds   = session.get_credentials().get_frozen_credentials()
    auth    = AWSV4SignerAuth(creds, region)

    client = OpenSearch(
        hosts=[{"host": opensearch_endpoint, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    BATCH_SIZE = 500
    for i in tqdm(range(0, len(docs), BATCH_SIZE), desc="Uploading batches"):
        batch = docs[i:i + BATCH_SIZE]
        success, _ = bulk(client, batch, request_timeout=60)
        print(f"Uploaded {success} documents")

if __name__ == "__main__":
    main()