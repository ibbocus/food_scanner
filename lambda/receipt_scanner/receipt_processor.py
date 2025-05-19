import logging
import os
import boto3
import re
from decimal import Decimal
import uuid
import json
from datetime import datetime
import sys


# Supermarket name detection dictionary
SUPERMARKETS = {
    "tesco": "Tesco",
    "sainsbury": "Sainsbury",
    "asda": "Asda",
    "morrisons": "Morrisons",
    "aldi": "Aldi",
    "lidl": "Lidl",
    "waitrose": "Waitrose",
    "co-op": "Co-op",
    "co op": "Co-op",
    "coop": "Co-op"
}

# DynamoDB table name from environment
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.getenv('DDB_TABLE', 'ReceiptsTable')


# Detect supermarket chain from raw receipt text
def detect_supermarket(raw_text: str) -> str:
    """
    Scan raw receipt text for known supermarket names.
    Returns the matching chain display name, or None.
    """
    txt = raw_text.lower()
    for key, display in SUPERMARKETS.items():
        if key in txt:
            return display
    return None


def process_image(bucket, key):
    client = boto3.client('textract')
    response = client.analyze_expense(Document={'S3Object': {'Bucket': bucket, 'Name': key}})
    # Combine all SummaryFields text for fallback search
    all_summary = " ".join(
        f.get('ValueDetection', {}).get('Text', '')
        for f in response['ExpenseDocuments'][0].get('SummaryFields', [])
    )

    # 1) Try supermarket list detection
    merchant = detect_supermarket(all_summary)

    # 2) Fallback to VENDOR_NAME field if none matched
    if not merchant:
        for field in response['ExpenseDocuments'][0].get('SummaryFields', []):
            if field.get('Type', {}).get('Text') == 'VENDOR_NAME':
                merchant = field.get('ValueDetection', {}).get('Text')
                break
        else:
            merchant = 'Unknown'
    # Extract transaction date
    receipt_time = None
    for field in response['ExpenseDocuments'][0].get('SummaryFields', []):
        if field.get('Type', {}).get('Text') == 'TRANSACTION_DATE':
            receipt_time = field['ValueDetection']['Text']
    # Extract line items
    items = []
    for doc in response['ExpenseDocuments']:
        for group in doc.get('LineItemGroups', []):
            for item in group.get('LineItems', []):
                fields = item.get('LineItemExpenseFields', [])
                name = fields[0]['ValueDetection']['Text'] if len(fields) > 0 else ''
                raw_amount = fields[1]['ValueDetection']['Text'] if len(fields) > 1 else '0'
                cleaned = re.sub(r'[^\d\.\-]', '', raw_amount)
                amount = Decimal(cleaned) if cleaned else Decimal('0.0')
                items.append({'item': name, 'price': amount})
    return {'shop': merchant, 'items': items, 'source': key, 'receipt_time': receipt_time}

def save_to_dynamodb(record):
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=record)

def lambda_handler(event, context):
    logging.debug("Lambda invoked with event: %s", json.dumps(event, default=str))    
    for rec in event.get('Records', []):
        bucket = rec['s3']['bucket']['name']
        key = rec['s3']['object']['key']
        user_id = key.split('/')[0]
        upload_time = datetime.utcnow().isoformat()
        data = process_image(bucket, key)
        data.update({
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'upload_time': upload_time,
            'contents': data.pop('items')
        })
        save_to_dynamodb(data)
        logging.debug("Record saved to DynamoDB for id=%s", data["id"])
    return {'status': 'processed'}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "images/image.png"
    user_id = path.split("/")[0]
    upload_time = datetime.utcnow().isoformat()
    data = process_image(path)
    data.update({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "upload_time": upload_time,
        "contents": data.pop("items")
    })

    print(data)
    logging.debug("Generated record for DynamoDB: %s", json.dumps(data, default=str, indent=2))
    # Attempt to save to DynamoDB
    try:
        save_to_dynamodb(data)
        logging.debug("Successfully saved record to DynamoDB")
    except Exception as e:
        logging.error("Failed to save to DynamoDB: %s", e, exc_info=True)