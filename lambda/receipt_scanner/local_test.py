#!/usr/bin/env python3
import sys
import boto3
import json
import re
from decimal import Decimal
from datetime import datetime
import uuid

# Replace with your AWS region if needed
REGION = "us-east-1"

def analyze_receipt_bytes(image_path: str):
    """
    Read the given image file into bytes and call Textract AnalyzeExpense.
    Returns the full Textract response.
    """
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    client = boto3.client("textract", region_name=REGION)
    resp = client.analyze_expense(
        Document={'Bytes': img_bytes}
    )
    return resp

def dump_summary_fields(doc):
    print("\n=== SummaryFields ===")
    for field in doc.get("SummaryFields", []):
        t = field.get("Type", {}).get("Text", "")
        v = field.get("ValueDetection", {}).get("Text", "")
        print(f"{t:20} : {v}")

def dump_line_items(doc):
    print("\n=== LineItems ===")
    for group in doc.get("LineItemGroups", []):
        for item in group.get("LineItems", []):
            fields = item.get("LineItemExpenseFields", [])
            name = fields[0]['ValueDetection']['Text'] if len(fields) > 0 else ""
            raw_amt = fields[1]['ValueDetection']['Text'] if len(fields) > 1 else ""
            print(f"  - {name:30} | {raw_amt}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python local_test.py <path/to/receipt.jpg>")
        sys.exit(1)

    image_path = sys.argv[1]
    print(f"Analyzing local image: {image_path}\n")

    # For "local" tests, bypass S3 and use bytes
    response = analyze_receipt_bytes(image_path)

    docs = response.get("ExpenseDocuments", [])
    if not docs:
        print("No documents found in response.")
        return

    # Dump out all the raw text and fields
    for i, doc in enumerate(docs):
        print(f"\n----- Document #{i+1} -----")
        dump_summary_fields(doc)
        dump_line_items(doc)

    # Example: you can now pull out the date or merchant:
    summary = docs[0].get("SummaryFields", [])
    merchant = next(
        (f['ValueDetection']['Text'] 
         for f in summary 
         if f.get('Type', {}).get('Text') == 'VENDOR_NAME'),
        "Unknown"
    )
    txn_date = next(
        (f['ValueDetection']['Text']
         for f in summary
         if f.get('Type', {}).get('Text') == 'TRANSACTION_DATE'),
        "Unknown"
    )
    print(f"\nDetected merchant: {merchant}")
    print(f"Transaction date : {txn_date}")

if __name__ == "__main__":
    main()