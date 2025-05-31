import logging
import os
import boto3
import re
from decimal import Decimal
import uuid
import json
from datetime import datetime, timezone
import sys

# ── Only the main UK supermarket chains (all keys in lowercase) ────────────────
SUPERMARKETS = {
    "tesco":     "Tesco",
    "sainsbury": "Sainsbury",
    "asda":      "Asda",
    "morrisons": "Morrisons",
    "aldi":      "Aldi",
    "lidl":      "Lidl",
    "waitrose":  "Waitrose",
    "co-op":     "Co-op",
    "co op":     "Co-op",
    "coop":      "Co-op",
    "Doritos":   "Doritos"
}

# DynamoDB table name from environment
dynamodb   = boto3.resource("dynamodb")
TABLE_NAME = os.getenv("DDB_TABLE", "ReceiptsTable")


def detect_supermarket(raw_text: str) -> str:
    """
    Scan raw receipt text for known UK supermarket names.
    Returns the matching chain display name, or None if none found.
    """
    txt = (raw_text or "").lower()
    for key, display in SUPERMARKETS.items():
        if key in txt:
            return display
    return None




def process_image(bucket, key, mode="default"):
    """
    1) Calls Textract AnalyzeExpense (or local) to extract a structured ExpenseDocument.
    2) Detects the supermarket (merchant) from the SummaryFields.
    3) Iterates each LineItem in all ExpenseDocuments → only if it contains
       a field with Type.Text == 'ITEM' and another with Type.Text == 'PRICE' (or 'TOTAL').
    4) Skips any line whose raw price ≤ 0 or whose item text contains certain keywords
       (e.g. "price saving", "balance", "change", "express", etc.).
    5) Cleans up the PRICE string to Decimal.
    6) Uses extract_brand_and_name(...) to assign brand + clean item_name.
    7) Returns a dict:
       {
         "shop": merchant,
         "items": [ { "item": "...", "brand": "...", "price": Decimal(...) }, ... ],
         "source": key,
         "receipt_time": "...ISO..." or None
       }
    """

    client = boto3.client("textract")

    # 1) Fetch the expense response from Textract (S3 or local)
    if mode == "local":
        with open(key, "rb") as f:
            img_bytes = f.read()
        response = client.analyze_expense(
            Document={"Bytes": img_bytes}
        )
    else:
        response = client.analyze_expense(
            Document={"S3Object": {"Bucket": bucket, "Name": key}}
        )

    # 2) Combine all SummaryFields text for a quick supermarket detection
    all_summary = " ".join(
        f.get("ValueDetection", {}).get("Text", "")
        for f in response["ExpenseDocuments"][0].get("SummaryFields", [])
    )

    merchant = detect_supermarket(all_summary)
    if not merchant:
        # Fallback to VENDOR_NAME if no known supermarket found
        for field in response["ExpenseDocuments"][0].get("SummaryFields", []):
            if field.get("Type", {}).get("Text") == "VENDOR_NAME":
                merchant = field.get("ValueDetection", {}).get("Text")
                break
        else:
            merchant = "Unknown"

    # 3) Extract transaction date (if present)
    receipt_time = None
    for field in response["ExpenseDocuments"][0].get("SummaryFields", []):
        if field.get("Type", {}).get("Text") == "TRANSACTION_DATE":
            receipt_time = field["ValueDetection"]["Text"]
            break

    # 4) Build the list of real line-items
    items = []
    # Keywords to filter out entirely “nonsense” lines
    SKIP_KEYWORDS = [
        "price saving",
        "balance",
        "change",
        "express",
        "price laut",   # e.g. "Price Lauting"
        "price sant",   # e.g. "Price Santing"
        "price sav",    # catch partial
    ]

    for doc in response["ExpenseDocuments"]:
        for group in doc.get("LineItemGroups", []):
            for item in group.get("LineItems", []):
                fields = item.get("LineItemExpenseFields", [])

                raw_name   = None
                raw_amount = None
                for f in fields:
                    fld_type  = f.get("Type", {}).get("Text", "")
                    fld_value = f.get("ValueDetection", {}).get("Text", "")
                    if fld_type == "ITEM":
                        raw_name = fld_value
                    elif fld_type in ("PRICE", "TOTAL"):
                        raw_amount = fld_value

                # Skip if we didn’t find both an ITEM and a PRICE/TOTAL
                if not raw_name or not raw_amount:
                    continue

                # 5) Clean up amount → Decimal
                cleaned = re.sub(r"[^\d\.\-]", "", raw_amount)
                try:
                    amount = Decimal(cleaned) if cleaned else Decimal("0.0")
                except Exception:
                    amount = Decimal("0.0")

                # 6) Discard any non-positive prices
                if amount <= 0:
                    continue

                # 7) Prepare item_name, brand, and first field
                item_name = raw_name.strip()
                brand = merchant
                tokens = item_name.split()
                if tokens:
                    first = tokens[0]
                else:
                    first = merchant

                # 8) Skip if item_name lowercased contains any of our “skip keywords”
                low = item_name.lower()
                if any(kw in low for kw in SKIP_KEYWORDS):
                    continue

                # 9) Everything OK → keep it
                items.append({
                    "item":  item_name,
                    "shop": merchant,
                    "first": first,
                    "price": amount
                })

    return {
        "shop":         merchant,
        "items":        items,
        "source":       key,
        "receipt_time": receipt_time
    }


def save_to_dynamodb(record):
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=record)


def lambda_handler(event, context):
    
    logging.debug("Lambda invoked with event: %s", json.dumps(event, default=str))
    for rec in event.get("Records", []):
        bucket    = rec["s3"]["bucket"]["name"]
        key       = rec["s3"]["object"]["key"]
        user_id   = key.split("/")[0]
        upload_ts = datetime.now(timezone.utc).isoformat()

        data = process_image(bucket, key)
        data.update({
            "id":           str(uuid.uuid4()),
            "user_id":      user_id,
            "upload_time":  upload_ts,
            "contents":     data.pop("items")
        })
        save_to_dynamodb(data)
        logging.debug("Record saved to DynamoDB for id=%s", data["id"])
    return {"status": "processed"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "images/receipt2.png"
    user_id = path.split("/")[0]
    upload_ts = datetime.now(timezone.utc).isoformat()

    data = process_image(None, path, mode="local")
    data.update({
        "id":          str(uuid.uuid4()),
        "user_id":     user_id,
        "upload_time": upload_ts,
        "contents":    data.pop("items")
    })

    print(json.dumps(data, default=str, indent=2))
    logging.debug("Generated record for DynamoDB: %s", json.dumps(data, default=str, indent=2))
    try:
        save_to_dynamodb(data)
        logging.debug("Successfully saved record to DynamoDB")
    except Exception as e:
        logging.error("Failed to save to DynamoDB: %s", e, exc_info=True)