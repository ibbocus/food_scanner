#!/usr/bin/env bash
set -euo pipefail

# Configuration
URL="https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
S3_PATH="s3://food-scanner-046873714594/db/openfoodfacts-products.jsonl"

# Stream-download, decompress, and upload to S3
curl -L "$URL" | gunzip | aws s3 cp - "$S3_PATH" --content-type "application/jsonl"
