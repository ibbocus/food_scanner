import os
import boto3
import re
from decimal import Decimal
import uuid

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
    return {'shop': merchant, 'items': items, 'source': os.path.basename(path)}

def save_to_dynamodb(record):
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=record)

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    for rec in event.get('Records', []):
        bucket = rec['s3']['bucket']['name']
        key = rec['s3']['object']['key']
        tmp_path = f"/tmp/{os.path.basename(key)}"
        s3.download_file(bucket, key, tmp_path)
        data = process_image(tmp_path)
        data['id'] = str(uuid.uuid4())
        save_to_dynamodb(data)
    return {'status': 'processed'}