import logging
import os
import boto3
import re
from decimal import Decimal
import uuid
import json
from datetime import datetime
import base64
from io import BytesIO

# DynamoDB table name from environment
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.getenv('DDB_TABLE', 'ReceiptsTable')
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization,user-id'
}

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
    # CORS preflight
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': ''
            }

        # API Gateway POST with image data
        if event.get('httpMethod') == 'POST':
            # Extract user_id from headers or default
            headers = event.get('headers', {})
            user_id = headers.get('user-id', 'anonymous')
            upload_time = datetime.utcnow().isoformat()

            # Decode image from body
            body = event.get('body', '')
            img_bytes = base64.b64decode(body) if event.get('isBase64Encoded') else body.encode('utf-8')
            tmp_path = '/tmp/uploaded.img'
            with open(tmp_path, 'wb') as f:
                f.write(img_bytes)

            # Process and save
            data = process_image(tmp_path)
            data.update({
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'upload_time': upload_time,
                'contents': data.pop('items')
            })
            save_to_dynamodb(data)

            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps(data, default=str)
            }
    except Exception as e:
        # 3) Error path must also include CORS headers
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(e)})
        }

    # Existing S3 event handling
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
    # If first arg is "--api", simulate API Gateway POST
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        # Next arg is path
        path = sys.argv[2] if len(sys.argv) > 2 else "images/receipt.jpg"
        user_id = path.split("/")[0]
        upload_time = datetime.utcnow().isoformat()
        # Read and base64-encode
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        event = {
            "httpMethod": "POST",
            "headers": {"user-id": user_id},
            "body": img_b64,
            "isBase64Encoded": True
        }
        resp = lambda_handler(event, None)
        logging.debug("API Gateway simulation response: %s", json.dumps(resp, default=str, indent=2))
        sys.exit(0)
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