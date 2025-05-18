import logging
import os
import boto3
import re
from decimal import Decimal
import uuid
import json
from datetime import datetime

# DynamoDB table name from environment
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.getenv('DDB_TABLE', 'ReceiptsTable')

def process_image(path):
    client = boto3.client('textract')
    with open(path, 'rb') as document:
        image_bytes = document.read()
    response = client.analyze_expense(Document={'Bytes': image_bytes})
    # Extract merchant name
    merchant = 'Unknown'
    if 'MerchantName' in response['ExpenseDocuments'][0]['SummaryFields'][0]:
        merchant = response['ExpenseDocuments'][0]['SummaryFields'][0]['ValueDetection']['Text']
    receipt_time = None
    for field in response['ExpenseDocuments'][0].get('SummaryFields', []):
        if field.get('Type', {}).get('Text') == 'TransactionDate':
            receipt_time = field.get('ValueDetection', {}).get('Text')
    # Extract line items
    items = []
    for doc in response['ExpenseDocuments']:
        for field in doc.get('LineItemGroups', []):
            for item_group in field.get('LineItems', []):
                name = item_group.get('LineItemExpenseFields', [])[0]['ValueDetection']['Text']
                raw_amount = item_group.get('LineItemExpenseFields', [])[1]['ValueDetection']['Text']
                # Remove currency symbols and commas
                cleaned = re.sub(r'[^\d\.\-]', '', raw_amount)
                amount = Decimal(cleaned) if cleaned else Decimal('0.0')
                items.append({'item': name, 'price': amount})
    print(items)
    return {'shop': merchant, 'items': items, 'source': os.path.basename(path), 'receipt_time': receipt_time}

def save_to_dynamodb(record):
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=record)

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    for rec in event.get('Records', []):
        bucket = rec['s3']['bucket']['name']
        key = rec['s3']['object']['key']
        user_id = key.split('/')[0]
        upload_time = datetime.utcnow().isoformat()
        tmp_path = f"/tmp/{os.path.basename(key)}"
        s3.download_file(bucket, key, tmp_path)
        data = process_image(tmp_path)
        data.update({
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'upload_time': upload_time,
            'contents': data.pop('items')
        })
        save_to_dynamodb(data)
    return {'status': 'processed'}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # Local debug runner
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "images/receipt.jpg"
    user_id = path.split("/")[0]
    upload_time = datetime.utcnow().isoformat()
    data = process_image(path)
    data.update({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "upload_time": upload_time,
        "contents": data.pop("items")
    })
    logging.debug("Generated record for DynamoDB: %s", json.dumps(data, default=str, indent=2))
    # Attempt to save to DynamoDB
    try:
        save_to_dynamodb(data)
        logging.debug("Successfully saved record to DynamoDB")
    except Exception as e:
        logging.error("Failed to save to DynamoDB: %s", e, exc_info=True)